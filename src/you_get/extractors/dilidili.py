#!/usr/bin/env python

__all__ = ['download']

from ..common import *
from ..extractor import *
from ..extractors.ckplayer import ckplayer_download

headers = {
    'DNT': '1',
    'Accept-Encoding': 'gzip, deflate, sdch, br',
    'Accept-Language': 'en-CA,en;q=0.8,en-US;q=0.6,zh-CN;q=0.4,zh;q=0.2',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.75 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Cache-Control': 'max-age=0',
    'Referer': 'http://www.dilidili.wang/',
    'Connection': 'keep-alive',
    'Save-Data': 'on',
}


class dilidili(VideoExtractor):
    name = 'dilidili'
    stream_types = [{'id': 'default'}]

    def prepare(self, **kwargs):
        index_html = get_content(self.url, headers=headers)
        self.title = match1(index_html, r'<title>(.+)丨(.+)</title>')  # title

        #  iframe load
        # http://player.jfrft.net/index.php?url=https://www.mgtv.com/b/322974/4337854.html
        frame_url = match1(index_html, r'<iframe .*?src=\"(.+?)\"')
        frame_html = get_content(frame_url, headers=headers, decoded=False).decode('utf-8')
        frame_host = match1(frame_url, r'(http://.*?)/')
        headers['Referer'] = frame_url

        # iframe player load, may derive from last iframe url, just mock their JS :)
        player_url = frame_host + '/' + match1(frame_html, r'<iframe .*?src=\"(.+?)\"')
        player_html = get_content(player_url, headers=headers, decoded=False).decode('utf-8')
        player_host = match1(frame_url, r'(http://.*?)/')
        headers['Referer'] = player_url
        headers['Origin'] = player_host

        # post to ``api.php`` for video info
        # api -> {url : str, play : str, type : str, success : str}
        api_params = json.loads(match1(player_html, r'.*?"api.php"\s*,\s*({.*})'))
        api_url = player_host + '/api.php'
        api_res = json.loads(post_content(api_url, post_data=api_params, headers=headers))
        if not api_res['url'].startswith('http'):
            api_res['url'] =  player_host + api_res['url']
        if 'http%3A%2F%2F' in api_res['url']:
            api_res['url'] = parse.unquote(api_res['url'])

        if api_res['success'] == '1':
            self.streams['default'] = api_res
        else:
            raise Exception('DILIDILI API ACCESS FAILED')

    def extract(self, **kwargs):
        data = self.streams.get('default')
        assert data
        if data['play'] in ('url', 'iframe', 'h5', 'html5', 'h5mp4'):
            _, data['container'], data['size'] = url_info(data['url'], headers=headers)
            data['src'] = [data['url']]
        elif data['play'] in ('hls', 'm3u8'):
            ts_urls = general_m3u8_extractor(data['url'], headers=headers)
            data['container'] = 'm3u8'
            data['size'] = urls_size(ts_urls)
            data['src'] = ts_urls
            data['m3u8_url'] = data['url']
        elif data['play'] in ('ajax'):
            # todo uncommon source ``aiqiyi, qq, youku``
            raise NotImplemented
        else:
            self.download = lambda **kwargs: ckplayer_download(data['url'], is_xml=True, title=self.title,
                                                               headers=headers, **kwargs)


site = dilidili()
download = site.download_by_url
download_playlist = playlist_not_supported('dilidili')