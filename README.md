# Bilibili 关注动态监控脚本



## 简介



本脚本用于监控哔哩哔哩（Bilibili）用户关注的 UP 主的动态，当有新视频发布时，会通过飞书机器人发送消息通知。脚本会自动处理登录、Cookie 管理和动态数据的比较，确保每次运行时能准确识别新视频。

### 功能特点:

1.  **自动登录**：支持扫码登录，自动处理 Cookie 的保存和验证。


2.  **动态监控**：定期检查关注的 UP 主的动态，识别新发布的视频。


3.  **消息推送**：通过飞书机器人发送包含视频信息的卡片消息。


4.  **数据比较**：使用临时文件和本地文件比较，确保只推送新视频。

## 安装与配置



### 1. 环境要求

*   Python 3.x


*   所需 Python 库：`requests`, `qrcode`, `schedule`

### 2. 安装依赖

```
pip install requests qrcode schedule
```

### 3. 配置文件路径

在脚本中，以下文件路径需要根据实际情况进行修改：


```
OLD\_BVID\_FILE = Path('/bili/old\_bvid.json')


COOKIE\_FILE = Path('/bili/cookie.txt')


JSON\_FILE = Path("/bili/jsonAll.json")


SAVE\_FILE = Path('/www/wwwroot/qr.png')
```

### 4. 配置飞书 Webhook

在脚本中，飞书 Webhook 地址需要替换为实际的地址：


```
FEISHU\_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxxxxxxxxxxxx
```

## 使用方法

### 1. 运行脚本

```
python bilibili\_followed\_dynamics.py
```

### 2. 扫码登录

如果本地没有有效的 Cookie，脚本会生成一个二维码并通过飞书机器人发送消息提醒。使用哔哩哔哩 App 扫描二维码进行登录。

### 3. 监控动态

登录成功后，脚本会定期检查关注的 UP 主的动态，并在有新视频发布时通过飞书机器人发送消息通知。

## 脚本说明

### 主要函数



*   `saveNprint_qr_image`：生成并保存二维码图片，并在控制台打印二维码。


*   `send_feishu_card_error`：发送飞书错误消息卡片。


*   `send_feishu_card`：发送飞书视频更新消息卡片。


*   `session_cookie` 类：处理登录、Cookie 管理和动态数据的比较。

    *   `dict_cookie_to_header`：将字典形式的 Cookie 转换为请求头中的 Cookie 字符串。


    *   `load_cookies`：加载本地 Cookie 文件。


    *   `cookie_valid`：验证 Cookie 的有效性。


    *   `save_cookies`：保存当前会话的 Cookie 到本地文件。


    *   `getQrCode`：生成并显示登录二维码。


    *   `ensure_login`：确保用户已登录，如果 Cookie 无效则进行扫码登录。


    *   `_wait_for_qr_login`：等待用户扫码登录。


    *   `compare_and_run`：比较当前动态数据和本地数据，判断是否有更新。


    *   `get_followed_dynamic`：获取关注的 UP 主的动态，识别新视频并发送消息通知。


*   `job`：定时任务函数，定期运行 `get_followed_dynamic` 函数。

### 定时任务

脚本使用 `schedule` 库实现定时任务，每次运行后会随机等待 1 - 3 分钟后再次运行。

**注意事项:**

*   请确保飞书 Webhook 地址的有效性，否则消息推送将失败。


*   脚本运行时需要有足够的权限来读写配置文件和临时文件。


*   如果二维码过期或失效，请重新运行脚本。
