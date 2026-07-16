from .setup import *
from .model import ModelItem
import requests
import re
import time
import cloudscraper
from pywebpush import webpush, WebPushException
import html
import os
import json
from tool import ToolNotify
import traceback
from urllib.parse import unquote
from datetime import timedelta

FLIGHT_DEPARTURE_ALLOW = ('인천', '김포', '청주')

site_map = {
    'ppomppu': '뽐뿌',
    'clien': '클리앙',
    'ruriweb': '루리웹',
    'coolenjoy' : '쿨엔조이',
    'quasarzone' : '퀘이사존',
    'snspring' : '청년이봄',
    'ybtour' : '노랑풍선',
    'ttang' : '땡처리',
    'modetour' : '모두투어'
}
board_map = {
    'ppomppu': '뽐뿌게시판',
    'ppomppu4': '해외뽐뿌',
    'ppomppu8': '알리뽐뿌',
    'money': '재태크포럼',
    'allsell': '사고팔고',
    'jirum': '알뜰구매',
    '1020': '핫딜/예판 유저',
    '600004': '핫딜/예판 업체',
    'qb_saleinfo': '지름/할인정보',
    'program_all': '전체프로그램',
    'discount_air': '특가항공권 전체',
    'today_air': '오늘오픈 특가항공',
    'discount_flight': '특가항공'
}
site_board_map = {
    'ppomppu': ['ppomppu', 'ppomppu4', 'ppomppu8', 'money'],
    'clien': ['allsell', 'jirum'],
    'ruriweb': ['1020', '600004'],
    'coolenjoy' : ['jirum'],
    'quasarzone': ['qb_saleinfo'],
    'snspring': ['program_all'],
    'ybtour': ['discount_air'],
    'ttang': ['today_air'],
    'modetour': ['discount_flight']
}


def get_url_prefix(site_name):
    url_prefix = ''
    if site_name == 'ppomppu':
        url_prefix = 'https://www.ppomppu.co.kr/zboard/'
    elif site_name == 'clien':
        url_prefix = 'https://www.clien.net'
    elif site_name == 'ruriweb':
        url_prefix = ''
    elif site_name == 'coolenjoy':
        url_prefix = ''
    elif site_name == 'quasarzone':
        url_prefix = ''
    elif site_name == 'snspring':
        url_prefix = 'https://snspring.or.kr/'
    elif site_name == 'ybtour':
        url_prefix = 'https://fly.ybtour.co.kr/booking/findDiscountAir.lts?isViewBfm=N&svcTpCode=FARE&efcCode=INV&efcBannerCode=&efcCityCode=&sortItem=&sortDir=ASC&efcCodeList=&onePageCnt=#'
    elif site_name == 'ttang':
        url_prefix = 'https://mm.ttang.com/ttangair/search/discount/today.do?trip=RT&gubun=T#'
    elif site_name == 'modetour':
        url_prefix = 'https://www.modetour.com/flights/discount-flight#'

    return url_prefix


class ModuleBasic(PluginModuleBase):
    def __init__(self, P):
        super(ModuleBasic, self).__init__(P, name='basic',
                                          first_menu='setting', scheduler_desc="핫딜 알람")
        self.db_default = {
            f'db_version': '2.0',
            f'{self.name}_auto_start': 'False',
            f'{self.name}_interval': '1',
            f'{self.name}_db_delete_day': '7',
            f'{self.name}_db_auto_delete': 'False',
            f'{P.package_name}_item_last_list_option': '',
            f'notify_mode': 'always',
            'use_site_ppomppu': 'False',
            'use_site_clien': 'False',
            'use_board_ppomppu_ppomppu': 'False',
            'use_board_ppomppu_ppomppu4': 'False',
            'use_board_ppomppu_ppomppu8': 'False',
            'use_board_ppomppu_money': 'False',
            'use_board_clien_allsell': 'False',
            'use_board_clien_jirum': 'False',
            'use_site_ruriweb': 'False',
            'use_board_ruriweb_1020': 'False',
            'use_board_ruriweb_600004': 'False',
            'use_site_coolenjoy': 'False',
            'use_board_coolenjoy_jirum': 'False',
            'use_site_quasarzone': 'False',
            'use_board_quasarzone_qb_saleinfo': 'False',
            'use_site_snspring': 'False',
            'use_board_snspring_program_all': 'False',
            'use_site_ybtour': 'False',
            'use_board_ybtour_discount_air': 'False',
            'use_site_ttang': 'False',
            'use_board_ttang_today_air': 'False',
            'use_site_modetour': 'False',
            'use_board_modetour_discount_flight': 'False',
            'use_hotdeal_alarm': 'False',
            'use_hotdeal_keyword_alarm': 'False',
            'use_hotdeal_keyword_alarm_dist' : 'False',
            'hotdeal_alarm_keyword': '',
            'alarm_message_template': '`{title}`\n{url}\n{mall_url}',
            'selenium_remote_address': '',
            'use_hotdeal_web_push' : 'True',
            'web_push_public_key' : '',
            'web_push_subscription' : '[]'
        }
        self.web_list_model = ModelItem

    def process_menu(self, sub, req):
        arg = P.ModelSetting.to_dict()
        if sub == 'setting':
            arg['is_include'] = F.scheduler.is_include(
                self.get_scheduler_name())
            arg['is_running'] = F.scheduler.is_running(
                self.get_scheduler_name())
            arg['apikey'] = F.SystemModelSetting.get('apikey')
        if sub == 'list':
            arg = self.web_list_model.get_list()
        return render_template(f'{P.package_name}_{self.name}_{sub}.html', arg=arg, site_map=site_map, board_map=board_map, site_board_map=site_board_map)

    def process_command(self, command, arg1, arg2, arg3, req):
        ret = {'ret': 'success'}
        if command == 'test':
            ret['status'] = 'warn'
            ret['title'] = '테스트'
            ret['data'] = '테스트 내용'
        return jsonify(ret)

    def scheduler_function(self):
        self.scrap_items()

    def scrap_detail(self):
        ret = {
            'status': 'success'
        }
        P.logger.info("scrap_details")
        regex = None
        items = ModelItem.get_non_shopping_mall_lsit()
        for item in items:
            mall_url = ''
            if item.site_name == 'ppomppu':
                regex = r'div class=wordfix>링크: \<a .+\>(?P<mall_url>.+)\</a\>'
            elif item.site_name == 'clien':
                regex = r'구매링크</span>.+>(?P<mall_url>.+)</a>'
            elif item.site_name == 'ruriweb':
                regex = r'<div class=\"source_url\">원본출처.+<a href=\".+\">(?P<mall_url>.+)</a>'
            elif item.site_name == 'coolenjoy':
                regex = r'alt=\"관련링크\">\s+<strong>(?P<mall_url>.+)</strong>'
            elif item.site_name == 'quasarzone':
                regex = r'<th>링크</th>\s+<td><a href=\".+\"\s+>(?P<mall_url>.+)</a>'
            if regex:
                if item.site_name == 'quasarzone':
                    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android', 'desktop': False})
                    getdata = scraper.get(get_url_prefix(item.site_name) + item.url)
                else:
                    sess = requests.session()
                    getdata = sess.get(get_url_prefix(item.site_name) + item.url)

                find_result = re.compile(regex).search(getdata.text)
                if find_result:
                    mall_url = find_result.groupdict().get('mall_url', '')
            item.mall_url = html.unescape(mall_url)
            ModelItem.save(item)
        return ret

    def scrap_items(self):
        ret = {
            'status': 'success',
            'data': []
        }
        P.logger.info("scrap_items")
        sess = requests.session()
        sess.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'})
        # get model settings.
        if P.ModelSetting.get('use_site_ppomppu') == 'True':
            boards = ['ppomppu', 'ppomppu4', 'ppomppu8', 'money']
            regex = r'title[\"\'] href=\"(?P<url>view\.php.+?)\"\s*>.+>(?P<title>.+)</span></a>'
            for board in boards:
                if P.ModelSetting.get(f'use_board_ppomppu_{board}') == 'True':

                    getdata = sess.get(
                        f'https://www.ppomppu.co.kr/zboard/zboard.php?id={board}')
                    matches = re.finditer(regex, getdata.text, re.MULTILINE)
                    for matchNum, match in enumerate(matches, start=1):
                        new_obj = match.groupdict()
                        new_obj['site'] = 'ppomppu'
                        new_obj['board'] = board
                        ret['data'].append(new_obj)

        if P.ModelSetting.get('use_site_clien') == 'True':
            boards = ['allsell', 'jirum']

            for board in boards:
                if board == 'allsell':
                    regex = r' class=\"list_subject\" href=\"(?P<url>.+?)\" .+\s+.+\s+.+?data-role=\"list-title-text\"\stitle=\"(?P<title>.+)\"\>'
                    url = f'https://www.clien.net/service/group/{board}'
                elif board == 'jirum':
                    regex = r'<span class=\"list_subject\" data-role=\"cut-string\" title=\"(?P<title>.+)\">\s+<a href=\"(?P<url>.+?)\"\s'
                    url = f'https://www.clien.net/service/board/{board}'

                if P.ModelSetting.get(f'use_board_clien_{board}') == 'True':
                    getdata = sess.get(url)
                    matches = re.finditer(regex, getdata.text, re.MULTILINE)
                    for matchNum, match in enumerate(matches, start=1):
                        new_obj = match.groupdict()
                        new_obj['site'] = 'clien'
                        new_obj['board'] = board
                        ret['data'].append(new_obj)

        if P.ModelSetting.get('use_site_ruriweb') == 'True':
            boards = ['1020', '600004']
            for board in boards:
                regex = r'<a class=\"deco\" href=\"(?P<url>.+)\"\>(?P<title>.+)</a>'
                url = f'https://bbs.ruliweb.com/market/board/{board}'
                if P.ModelSetting.get(f'use_board_ruriweb_{board}') == 'True':
                    getdata = sess.get(url)
                    matches = re.finditer(regex, getdata.text, re.MULTILINE)
                    for matchNum, match in enumerate(matches, start=1):
                        new_obj = match.groupdict()
                        new_obj['site'] = 'ruriweb'
                        new_obj['board'] = board
                        ret['data'].append(new_obj)

        if P.ModelSetting.get('use_site_coolenjoy') == 'True':
            boards = ['jirum']
            for board in boards:
                regex = r'<td class=\"td_subject\">\s+<a href=\"(?P<url>.+)\">\s+(?:<font color=.+?>)?(?P<title>.+?)(?:</font>)?\s+<span class=\"sound_only\"'
                url = f'https://coolenjoy.net/bbs/{board}'
                if P.ModelSetting.get(f'use_board_coolenjoy_{board}') == 'True':
                    getdata = sess.get(url)
                    matches = re.finditer(regex, getdata.text, re.MULTILINE)
                    for matchNum, match in enumerate(matches, start=1):
                        new_obj = match.groupdict()
                        new_obj['site'] = 'coolenjoy'
                        new_obj['board'] = board
                        ret['data'].append(new_obj)

        if P.ModelSetting.get('use_site_quasarzone') == 'True':
            boards = ['qb_saleinfo']
            scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android', 'desktop': False})
            for board in boards:
                regex = r'<p class=\"tit\">\s+<a href=\"(?P<url>.+)\"\s+class=.+>\s+.+\s+(?:<span class=\"ellipsis-with-reply-cnt\">)?(?P<title>.+?)(?:</span>)'
                url = f'https://quasarzone.com/bbs/{board}'
                if P.ModelSetting.get(f'use_board_quasarzone_{board}') == 'True':
                    getdata = scraper.get(url)
                    matches = re.finditer(regex, getdata.text, re.MULTILINE)
                    for matchNum, match in enumerate(matches, start=1):
                        new_obj = match.groupdict()
                        new_obj['site'] = 'quasarzone'
                        new_obj['board'] = board
                        new_obj['url'] = 'https://quasarzone.com' + new_obj['url'] if new_obj['url'].startswith('/') else new_obj['url']
                        ret['data'].append(new_obj)

        if P.ModelSetting.get('use_site_snspring') == 'True':
            boards = ['program_all']
            for board in boards:
                regex = r'<a href=\"(?P<url>programView\.do\?idx=\d+)\">(?:(?!</a>)[\s\S])*?class=\"txt01 program_title\">(?P<title>.+?)</span>'
                url = 'https://snspring.or.kr/programList.do'
                if P.ModelSetting.get(f'use_board_snspring_{board}') == 'True':
                    getdata = sess.get(url)
                    matches = re.finditer(regex, getdata.text, re.MULTILINE)
                    for matchNum, match in enumerate(matches, start=1):
                        new_obj = match.groupdict()
                        new_obj['site'] = 'snspring'
                        new_obj['board'] = board
                        ret['data'].append(new_obj)

        if P.ModelSetting.get('use_site_ybtour') == 'True':
            boards = ['discount_air']
            for board in boards:
                regex = r'<tr[^>]*id=\"fareListSeq_\d+\">[\s\S]*?<span>(?P<air>[^<]+)</span>[\s\S]*?<td class=\"tft_str\">(?P<dep>[^<]+)</td>[\s\S]*?<span class=\"ellipsis\">(?P<arr>[^<]+)</span>[\s\S]*?(?P<price>[\d,]+)\s*원[\s\S]*?<td class=\"tft_dat\">(?P<date>[^<]+)</td>[\s\S]*?<td class=\"tft_pan\">(?P<trip>[^<]+)</td>[\s\S]*?name=\"efmAfsId\" value=\"(?P<afsid>[^\"]+)\"'
                url = 'https://fly.ybtour.co.kr/booking/findDiscountAir.lts?isViewBfm=N&svcTpCode=FARE&efcCode=INV&efcBannerCode=&efcCityCode=&sortItem=&sortDir=ASC&efcCodeList=&onePageCnt='
                if P.ModelSetting.get(f'use_board_ybtour_{board}') == 'True':
                    getdata = sess.get(url)
                    matches = re.finditer(regex, getdata.text, re.MULTILINE)
                    for matchNum, match in enumerate(matches, start=1):
                        item = match.groupdict()
                        if item['dep'] not in FLIGHT_DEPARTURE_ALLOW:
                            continue
                        new_obj = {
                            'site': 'ybtour',
                            'board': board,
                            'url': item['afsid'],
                            'title': f"[{item['trip']}] {item['dep']}→{item['arr']} {item['air']} {item['price']}원~ ({item['date']})"
                        }
                        ret['data'].append(new_obj)

        if P.ModelSetting.get('use_site_ttang') == 'True':
            boards = ['today_air']
            for board in boards:
                url = 'https://mm.ttang.com/ttangair/search/discount/listAct.do'
                referer = 'https://mm.ttang.com/ttangair/search/discount/today.do?trip=RT&gubun=T'
                if P.ModelSetting.get(f'use_board_ttang_{board}') == 'True':
                    params = {
                        'trip': 'RT', 'dep0': '', 'arr0': '', 'dep1': '', 'arr1': '', 'dep2': '', 'arr2': '',
                        'dep0Name': '', 'arr0Name': '', 'dep1Name': '', 'arr1Name': '', 'dep2Name': '', 'arr2Name': '',
                        'depdate0': '', 'depdate1': '', 'depdate2': '',
                        'adt': '1', 'chd': '0', 'inf': '0',
                        'comp': '', 'car': '', 'groupId': '', 'pflAffId': '', 'pflAfsId': '',
                        'gubun': 'T', 'seq': '', 'requestData': '',
                        'page': '1', 'scale': '200', 'totalCnt': '0'
                    }
                    getdata = sess.post(url, data=params, headers={'X-Requested-With': 'XMLHttpRequest', 'Referer': referer})
                    cdata_match = re.search(r'<!\[CDATA\[(.*?)\]\]>', getdata.text, re.DOTALL)
                    if cdata_match and cdata_match.group(1):
                        payload = json.loads(cdata_match.group(1))
                        for item in payload.get('response', []):
                            if item.get('depCityDesc') not in FLIGHT_DEPARTURE_ALLOW:
                                continue
                            trip = '왕복' if item.get('tripType') == 'RT' else '편도'
                            from_d, to_d = item.get('fromSupplyDate', ''), item.get('toSupplyDate', '')
                            if len(from_d) == 8 and len(to_d) == 8:
                                date_str = f"{from_d[2:4]}/{from_d[4:6]}/{from_d[6:8]}~{to_d[2:4]}/{to_d[4:6]}/{to_d[6:8]}"
                            else:
                                date_str = f"{from_d}~{to_d}"
                            new_obj = {
                                'site': 'ttang',
                                'board': board,
                                'url': item.get('masterId', ''),
                                'title': f"[{trip}] {item.get('depCityDesc','')}→{item.get('arrCityDesc','')} {item.get('tktCarDesc','')} {item.get('totalPrice',0):,}원~ ({date_str})"
                            }
                            ret['data'].append(new_obj)

        if P.ModelSetting.get('use_site_modetour') == 'True':
            boards = ['discount_flight']
            for board in boards:
                if P.ModelSetting.get(f'use_board_modetour_{board}') == 'True':
                    sess.get('https://www.modetour.com/flights/discount-flight')
                    raw_ctx = sess.cookies.get('ModeEcommerceContext')
                    if raw_ctx:
                        ctx = json.loads(unquote(raw_ctx))
                        api_header = json.dumps({
                            'webSiteNo': ctx.get('webSiteNo'),
                            'companyNo': ctx.get('companyNo'),
                            'deviceType': ctx.get('deviceType'),
                            'apiKey': ctx.get('apiKey')
                        })
                        dep_date = datetime.now().strftime('%Y-%m-%d')
                        arr_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
                        params = {
                            'departureCity': '', 'continentCode': 'ASIA', 'arrivalCity': '',
                            'departureDate': dep_date, 'arrivalDate': arr_date,
                            'page': 1, 'itemCount': 200
                        }
                        getdata = sess.get('https://b2c-api.modetour.com/DiscountFlight/GetList',
                                            params=params, headers={'ModeWebApiReqHeader': api_header})
                        try:
                            payload = getdata.json()
                        except Exception:
                            payload = {}
                        for item in payload.get('result', []):
                            dep = (item.get('departure') or {}).get('value')
                            if dep not in FLIGHT_DEPARTURE_ALLOW:
                                continue
                            arr = (item.get('arrival') or {}).get('value', '')
                            air = (item.get('air') or {}).get('value', '')
                            adult = item.get('adult') or {}
                            total_price = adult.get('value', 0) + adult.get('tax', 0) + adult.get('tax2', 0)
                            sdate = (item.get('sDate') or {}).get('value', '')
                            edate = (item.get('eDate') or {}).get('value', '')
                            new_obj = {
                                'site': 'modetour',
                                'board': board,
                                'url': str(item.get('stockPackageNo', '')),
                                'title': f"{dep}→{arr} {air} {total_price:,}원 ({sdate}~{edate})"
                            }
                            ret['data'].append(new_obj)

        for row in ret['data']:
            ModelItem.update({
                'site_name': row['site'],
                'board_name': row['board'],
                'title': row['title'].replace('</span>',''),
                'url':  row['url']
            })
        self.process_discord_data()
        return ret

    def process_discord_data(self):
        try:
            self.scrap_detail()
        except Exception as e:
            P.logger.error('Exception:%s', e)
            P.logger.error(traceback.format_exc())
        items = ModelItem.get_alarm_target_list()
        if items is None or len(items) == 0:
            return
        msg_template = P.ModelSetting.get('alarm_message_template')
        if msg_template is None or len(msg_template) == 0:
            return
        for item in items:
            if P.ModelSetting.get_bool('use_hotdeal_alarm') or P.ModelSetting.get_bool('use_hotdeal_keyword_alarm'):
                title = item.title.replace('&gt;', '>').replace('&lt;', '<')
                site = site_map[item.site_name]
                board = board_map[item.board_name]
                url = get_url_prefix(site_name=item.site_name)+item.url
                mall_url = item.mall_url if item.mall_url and len(
                    item.mall_url) > 0 else ''
                is_send = False
                is_dist_send = False
                is_web_push = P.ModelSetting.get_bool('use_hotdeal_web_push')

                keywords = P.ModelSetting.get('hotdeal_alarm_keyword').split(',')
                if P.ModelSetting.get_bool('use_hotdeal_alarm'):
                    is_send = True
                else:
                    is_send = False
                    is_dist_send = False
                for keyword in keywords:
                    if P.ModelSetting.get_bool('use_hotdeal_keyword_alarm'):
                        if len(keyword) > 0 and keyword.lower() in title.lower():
                            is_send = True
                    if P.ModelSetting.get_bool('use_hotdeal_keyword_alarm_dist'):
                        if len(keyword) > 0 and keyword.lower() in title.lower():
                            is_dist_send = True
                        

                if is_send is True:
                    msg = msg_template
                    msg = msg.replace('{title}', title).replace('{site}', site).replace(
                        '{board}', board).replace('{mall_url}', mall_url).replace('{url}', url)
                    ToolNotify.send_message(
                        msg, message_id=f"bot_{P.package_name}")
                    if is_web_push:
                        self.web_push({'message' : title, 'url':mall_url if len(mall_url) > 0 else url})
                if is_dist_send is True:
                    msg = msg_template
                    msg = msg.replace('{title}', title).replace('{site}', site).replace(
                        '{board}', board).replace('{mall_url}', mall_url).replace('{url}', url)
                    ToolNotify.send_message(
                        msg, message_id=f"bot_{P.package_name}_keyword")
                    if is_web_push:
                        self.web_push({'message' : title, 'url':mall_url if len(mall_url) > 0 else url})
            item.alarm_status = True
            ModelItem.save(item)
    def process_api(self, sub, req):
        result = ''
        if sub == 'web_push_init':
            if not os.path.exists('/data/web_push'):
                os.mkdir('/data/web_push')
            gen_key_result = os.popen("cd /data/web_push ; /usr/local/bin/vapid --applicationServerKey --gen").read()
            key = gen_key_result.split(' = ')[1].strip()
            P.logger.info(key)
            with open('/data/web_push/key.txt','w') as file:
                file.write(key)
            P.ModelSetting.set('web_push_public_key', key)
            result = json.dumps({'key' : key})

        elif sub =='web_push_subscribe':
            P.logger.info(req.get_json())
            subscription_info = req.get_json()
            subscription_info.pop('apikey', None)
            web_push_subscription = json.loads(P.ModelSetting.get('web_push_subscription'))
            if type(web_push_subscription) != list:
                web_push_subscription = []
            if subscription_info not in  web_push_subscription:
                web_push_subscription.append(subscription_info)
            P.ModelSetting.set('web_push_subscription', json.dumps(web_push_subscription))
            return subscription_info

        elif sub == 'web_push' :
            push_data = req.get_json()
            push_data.pop('apikey', None)
            self.web_push(push_data)
            result = json.dumps({'status' : 'success'})
        elif sub == 'web_push_reset' :
            P.ModelSetting.set('web_push_subscription', '[]')
        return result
    def web_push(self, data):
        P.logger.info(data)
        infos = json.loads(P.ModelSetting.get('web_push_subscription'))
        result = []
        for info in infos:
            try:
                result.append(webpush(
                    subscription_info = info,
                    data = json.dumps(data),
                    vapid_private_key='/data/web_push/private_key.pem',
                    vapid_claims = {
                        'sub' : 'mailto:dbswnschl@gmail.com'
                    }
                ))
            except:
                P.logger.error(traceback.format_exc())
                continue