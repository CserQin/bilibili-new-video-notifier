import random
import requests, qrcode, time, re, json, os, tempfile, filecmp, shutil, schedule
from pathlib import Path
import requests.utils as ru
from datetime import datetime

HEADERS = {
    'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
    'Accept': '*/*',
    'Host': 'passport.bilibili.com',
    'Connection': 'keep-alive'
}

# -----------运行地址-----------
OLD_BVID_FILE = Path('/bili/old_bvid.json')
COOKIE_FILE = Path('/bili/cookie.txt')
JSON_FILE = Path("/bili/jsonAll.json")
SAVE_FILE = Path('/www/wwwroot/qr.png')
#↑↑服务器公网链接展示图片

session = requests.Session()

def saveNprint_qr_image(text: str, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img = qrcode.make(text)
    img.save(path)
    print("二维码已保存到", path)
    qr = qrcode.QRCode(border=1)
    qr.add_data(text)
    qr.print_ascii(invert=True)

def send_feishu_card_error(error_str: str):
    elements = []
    # 添加错误信息
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": (
                f"**系统提示：** {error_str}  \n"
                f"**时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n"
            )
        }
    })
    elements.append({
        "tag": "action",
        "actions": [{
            "tag": "button",
            "text": {"tag": "plain_text", "content": "👉 扫码登录"},
            "type": "primary",
            "url": ""  # 替换为实际的链接地址
        }]
    })
    elements.append({"tag": "hr"})

    # 飞书 Webhook 地址
    FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/"

    # 构造卡片消息
    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "⚠️ 系统错误通知"},
                "template": "red"
            },
            "elements": elements
        }
    }

    # 发送请求
    resp = requests.post(FEISHU_WEBHOOK, json=card, timeout=10)
    print("飞书推送结果：", resp.json())


def send_feishu_card(videos: list[dict]):
    if not videos:
        return

    elements = []
    for v in videos:
        # 纯文本段落 + 超链接按钮
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"**UP：**{v['name']}  \n"
                    f"**时间：**{v['pub_ts']}  \n"
                    f"**标题：**{v['title']}"
                )
            }
        })
        elements.append({
            "tag": "action",
            "actions": [{
                "tag": "button",
                "text": {"tag": "plain_text", "content": "👉 打开视频"},
                "type": "primary",
                "url": f"https://www.bilibili.com/video/{v['bvid']}"
            }]
        })
        elements.append({"tag": "hr"})

    FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/"
    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "🎞 关注的 UP 更新视频啦！"},
                "template": "blue"
            },
            "elements": elements
        }
    }

    resp = requests.post(FEISHU_WEBHOOK, json=card, timeout=10)
    print("飞书推送结果：", resp.text)

class session_cookie:

    # cookie形式转换
    def dict_cookie_to_header(self, dict_cookie_str: str) -> str:
        # 1. 提取字典部分
        m = re.search(r'\{.*?\}', dict_cookie_str, flags=re.S)
        if not m:
            raise ValueError('未找到字典部分')
        cookie_dict = eval(m.group())
        # 2. 第一段里所有“公共字段”的模板（除了下面 5 个会动态替换）
        # 经过测试以上【xxxx】内容需要根据抓包去获得固定值（每个用户不同），
        # 每次提交的5个实际值才是有效字段，
        # 没有固定值却无法正常访问
        template = (
            "buvid3=xxxx; "
            "b_nut=xxxx; "
            "_uuid=xxxx; "
            "header_theme_version=OPEN; "
            "enable_web_push=DISABLE; "
            "home_feed_column=4; "
            "browser_resolution=xxx; "
            "buvid4=xxxxx; "
            "DedeUserID={DedeUserID}; "
            "DedeUserID__ckMd5={DedeUserID__ckMd5}; "
            "theme-tip-show=SHOWED; "
            "rpdid=xxxx; "
            "theme-avatar-tip-show=SHOWED; "
            "CURRENT_QUALITY=80; "
            "CURRENT_FNVAL=4048; "
            "bsource=search_baidu; "
            "fingerprint=xxxx; "
            "buvid_fp_plain=undefined; "
            "buvid_fp=xxxxx; "
            "bili_ticket=xxxxx; "
            "bili_ticket_expires=xxxx; "
            "SESSDATA={SESSDATA}; "
            "bili_jct={bili_jct}; "
            "sid={sid}; "
            "bp_t_offset_140462390=xxxxx; "
            "b_lsid=xxxxx"
        )    
        # 3. 把字典里的值填进去
        header_cookie = template.format(**cookie_dict)
        return f"Cookie: {header_cookie}"

    def __init__(self):
        self.sess = requests.Session()
        self.sess.headers.update(HEADERS)
        self.load_cookies()

    def load_cookies(self):
        if COOKIE_FILE.exists() and COOKIE_FILE.stat().st_size > 0:
            try:
                with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                    cookie_str = f.read().strip()
                    self.sess.headers['Cookie'] = self.dict_cookie_to_header(cookie_str)
                print("已加载本地 Cookie")
            except Exception as e:
                print("Cookie 文件损坏，已删除，准备重新登录", e)
                COOKIE_FILE.unlink(missing_ok=True)
        else:
            print("本地无 Cookie,准备登录")

    def cookie_valid(self) -> bool:
        try:
            if not COOKIE_FILE.exists():
                self._notify_and_save_qr("Cookie 文件不存在")
                return False

            url = "https://api.bilibili.com/x/space/myinfo"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://space.bilibili.com/',
                'Cookie': self.dict_cookie_to_header(COOKIE_FILE.read_text(encoding='utf-8').strip())
            }
            r = requests.get(url, headers=headers, timeout=10)
            data = r.json()
            if data.get("code") == 0 and data.get("data", {}).get("mid"):
                return True
        except Exception as e:
            print("Cookie 校验异常:", e)

        # 失效 → 提醒 + 保存二维码
        self._notify_and_save_qr("Cookie 已失效，需重新扫码登录")
        return False

    def _notify_and_save_qr(self, msg: str):
        time.sleep(1)
        # 飞书提醒
        send_feishu_card_error(msg)
        gen_url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/generate'
        resp = self.sess.get(gen_url).json()
        login_url = re.search(r'(https?://[^\s<]+)', resp['data']['url']).group(0)
        saveNprint_qr_image(login_url, SAVE_FILE)

    def save_cookies(self):
        with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
            json.dump(ru.dict_from_cookiejar(self.sess.cookies), f, ensure_ascii=False)
        print("Cookie 已保存到", COOKIE_FILE)

    def getQrCode(self):
        gen_url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/generate'
        resp = self.sess.get(gen_url).json()
        self.qrcode_key = resp['data']['qrcode_key']  # 保存 qrcode_key
        login_url = re.search(r'(https?://[^\s<]+)', resp['data']['url']).group(0)
        self._notify_and_save_qr(login_url)
        print(login_url)
        saveNprint_qr_image(login_url, SAVE_FILE)
        print(login_url)
        print('请使用哔哩哔哩 App 扫描二维码，qrcode_key =', self.qrcode_key)

    def ensure_login(self):
        if self.cookie_valid():
            print("✅ Cookie 有效，已登录")
            return True  # 返回 True 表示登录成功

        print("❌ Cookie 无效或未登录，开始扫码登录")
        self._notify_and_save_qr("Cookie 已失效，需重新扫码登录")
        return self._wait_for_qr_login()  # 等待扫码成功

    def _wait_for_qr_login(self) -> bool:
        self.getQrCode()  # 显示二维码
        poll_url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/poll'
        while True:
            time.sleep(5)  # 每 5 秒轮询一次
            poll_resp = self.sess.get(poll_url, params={'qrcode_key': self.qrcode_key}).json()
            code = poll_resp['data']['code']
            if code == 0:  # 登录成功
                print("🎉 扫码成功，登录完成")
                self.save_cookies()  # 保存 Cookie
                return True
            elif code == 86101:  # 未扫描
                print("等待扫码中...")
            elif code == 86090:  # 已扫描未确认
                print("已扫描，等待确认...")
            elif code in (86038, 86039):  # 二维码过期 / 失效
                print("二维码已失效，请重新运行脚本")
                return False
            else:
                print("未知状态:", poll_resp)
                return False

    def compare_and_run(self, resp: dict) -> bool:
        """返回 True 表示有更新"""
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as tmp:
            json.dump(resp, tmp, ensure_ascii=False, indent=2, sort_keys=True)
            tmp_path = tmp.name

        try:
            if JSON_FILE.exists() and filecmp.cmp(tmp_path, JSON_FILE, shallow=False):
                return False
            else:
                shutil.move(tmp_path, JSON_FILE)
                return True
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def get_followed_dynamic(self):
        Url_followed_dynamics = 'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/all?type=all&page=1&features=itemOpusStyle'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.bilibili.com/',
            'Host': 'api.bilibili.com'
        }
        resp = self.sess.get(Url_followed_dynamics, headers=headers).json()
        has_update = self.compare_and_run(resp)
        if not JSON_FILE.exists():
            print("首次运行，本地无旧数据，视为更新。")
        # 写json
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(resp, f, ensure_ascii=False)
        time.sleep(1)

        # 读json
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        items = data.get('data', {}).get('items', [])

        videos = []
        for item in items:
            if item.get('type') != 'DYNAMIC_TYPE_AV':
                continue
            archive = item.get('modules', {}).get('module_dynamic', {}).get('major', {}).get('archive', {})
            if not archive.get('bvid'):
                continue
            videos.append({
                'name': item['modules']['module_author']['name'],
                'pub_ts': datetime.fromtimestamp(item['modules']['module_author']['pub_ts']).strftime('%Y-%m-%d %H:%M:%S'),
                'title': archive['title'],
                'bvid': archive['bvid']
            })

        # 读取旧 bvid 列表，文件不存在或空/损坏都返回空集合
        try:
            with OLD_BVID_FILE.open(encoding='utf-8') as f:
                content = f.read().strip()
                old_bvids = set(json.loads(content) if content else [])
        except (FileNotFoundError, json.JSONDecodeError):
            old_bvids = set()
        new_videos = [v for v in videos if v['bvid'] not in old_bvids]

        if new_videos:
            send_feishu_card(new_videos)
            # 保存本轮全部 bvid 供下次差分
            json.dump([v['bvid'] for v in videos], OLD_BVID_FILE.open('w', encoding='utf-8'))
        else:
            print("本次无新增视频，不推送")

def job():
    bililogin = session_cookie()
    if bililogin.ensure_login():  # 等待登录成功
        print(f"[{datetime.now():%H:%M:%S}] 开始抓取...")
        bililogin.get_followed_dynamic()
    else:
        print("登录失败，无法继续抓取")

randnum = random.randint(1, 3)
schedule.every(randnum).minutes.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)