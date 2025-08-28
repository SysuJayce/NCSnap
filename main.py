#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# NetCup SCP 快照自动管理工具

from DrissionPage import ChromiumPage, ChromiumOptions
from datetime import datetime, timezone, timedelta
import time
import logging
import os
import sys
import json

# 设置北京时区
BEIJING_TZ = timezone(timedelta(hours=8))

# 自定义日志格式器，使用北京时间
class BeijingFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        # 将时间戳转换为北京时间
        dt = datetime.fromtimestamp(record.created, tz=BEIJING_TZ)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime('%H:%M:%S')

# 配置日志记录器
handler = logging.StreamHandler()
handler.setFormatter(BeijingFormatter(
    fmt='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

def get_beijing_time():
    """获取当前北京时间"""
    return datetime.now(tz=BEIJING_TZ)

def mask_string(text, show_start=2, show_end=2):
    """对字符串进行脱敏处理"""
    if len(text) <= show_start + show_end:
        return text
    return text[:show_start] + '*' * (len(text) - show_start - show_end) + text[-show_end:]

def load_config():
    """从JSON配置文件加载配置"""
    config_file = 'config.json'
    
    # 检查配置文件是否存在
    if not os.path.exists(config_file):
        logger.error(f"配置文件 {config_file} 不存在")
        sys.exit(1)
    
    try:
        # 读取并解析JSON配置文件
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 验证配置文件结构
        if 'accounts' not in config:
            logger.error("配置文件缺少 'accounts' 字段")
            sys.exit(1)
        
        if not isinstance(config['accounts'], list) or len(config['accounts']) == 0:
            logger.error("accounts 必须是非空数组")
            sys.exit(1)
        
        # 验证并处理每个账户的配置
        for i, account in enumerate(config['accounts']):
            # 检查必需字段
            required_fields = ['username', 'password', 'servers']
            for field in required_fields:
                if field not in account:
                    logger.error(f"账户 {i+1} 缺少必需字段: {field}")
                    sys.exit(1)
            
            # 验证服务器列表
            if not isinstance(account['servers'], list) or len(account['servers']) == 0:
                logger.error(f"账户 {i+1} 的 servers 必须是非空数组")
                sys.exit(1)
            
            # 处理服务器配置
            for j, server in enumerate(account['servers']):
                if isinstance(server, str):
                    # 兼容旧格式，转换为新格式
                    account['servers'][j] = {
                        'name': server,
                        'snap_count': 3  # 默认保留3个快照
                    }
                elif isinstance(server, dict):
                    # 新格式，检查必需字段
                    if 'name' not in server:
                        logger.error(f"账户 {i+1} 服务器 {j+1} 缺少 'name' 字段")
                        sys.exit(1)
                    
                    # 设置默认snap_count
                    if 'snap_count' not in server:
                        server['snap_count'] = 3
                    
                    # 验证snap_count
                    if not isinstance(server['snap_count'], int) or server['snap_count'] < 1:
                        logger.error(f"账户 {i+1} 服务器 {j+1} 的 snap_count 必须是正整数")
                        sys.exit(1)
                else:
                    logger.error(f"账户 {i+1} 服务器配置格式错误")
                    sys.exit(1)
        
        return config['accounts']
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON配置文件格式错误: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"读取配置文件失败: {str(e)}")
        sys.exit(1)

def setup_browser():
    """设置浏览器选项"""
    co = ChromiumOptions()
    
    # 无头模式和基本设置
    co.headless()
    co.incognito()
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-extensions')
    co.set_argument('--window-size=1920,1080')
    co.no_imgs(True)
    
    return co

def login_scp(page, username, password):
    """登录NetCup SCP管理面板"""
    logger.info("正在登录...")
    
    # 访问登录页面
    page.get('https://www.servercontrolpanel.de/SCP/Login')
    page.ele('@name:username')
    time.sleep(2)
    
    # 输入登录凭据并提交
    page.ele('@name:username').input(username)
    page.ele('@name:password').input(password)
    page.ele('@type:submit').click()
    
    time.sleep(3)
    
    # 检查登录结果
    current_url = page.url
    if '/Login' in current_url:
        logger.error("登录失败: 账号或密码错误")
        raise Exception("登录失败")
    else:
        logger.info("登录成功")
        return True

def select_server(page, server_name):
    """选择指定服务器"""
    # 等待服务器选择器加载
    page.ele('@id:navSelect')
    time.sleep(2)
    
    # 点击下拉菜单
    select_button = page.ele('css:.btn.dropdown-toggle')
    select_button.click()
    time.sleep(1)
    
    # 搜索并选择服务器
    search_box = page.ele('css:.bs-searchbox input')
    search_box.input(server_name)
    time.sleep(1)
    
    server_link = page.ele(f'xpath://a[contains(text(), "{server_name}")]')
    server_link.click()
    
    logger.info("  服务器选择完成")

def navigate_to_snapshots(page):
    """导航到快照管理页面"""
    # 进入Media菜单
    page.ele('@id:vServerpane_media')
    time.sleep(2)
    page.ele('@id:vServerpane_media').click()
    
    # 进入Snapshots子菜单
    page.ele('@id:sub_media_snapshot')
    time.sleep(2)
    page.ele('@id:sub_media_snapshot').click()
    
    # 等待页面加载
    page.ele('@id:snapshotName')
    time.sleep(2)
    
    logger.info("  已进入快照管理页面")

def get_snapshot_info(page):
    """获取当前快照信息"""
    try:
        # 获取快照表格中的所有行
        snapshot_rows = page.eles('xpath://table[@class="table table-striped"]//tbody/tr')
        
        valid_snapshots = []
        for row in snapshot_rows:
            name_cell = row.ele('tag:td')
            if name_cell and name_cell.text.strip():
                valid_snapshots.append(name_cell.text.strip())
        
        return len(valid_snapshots), valid_snapshots
        
    except Exception as e:
        logger.warning(f"  获取快照信息失败: {str(e)}")
        return 0, []

def create_snapshot(page):
    """创建新快照"""
    # 生成快照名称（使用北京时间）
    beijing_time = get_beijing_time()
    snapshot_name = beijing_time.strftime("%Y%m%d%H%M%S")
    
    logger.info(f"  创建快照: {snapshot_name}")
    
    # 填写快照信息并创建
    page.ele('@id:snapshotName').input(snapshot_name)
    page.ele('@id:snapshotDescription').input("Auto snapshot")
    page.ele('xpath://a[contains(@onclick, "sendCreateSnapshotForm")]').click()
    
    # 监控创建进度
    progress_states = set()
    
    while True:
        time.sleep(1)
        
        # 检查服务器停止状态
        stop_text = page.ele('@id:vServerJob_KVMSnapshot.stop_text')
        if stop_text and "stopped" in stop_text.text and "stopped" not in progress_states:
            logger.info("    服务器已停止")
            progress_states.add("stopped")
        
        # 检查快照创建状态
        create_text = page.ele('@id:vServerJob_KVMSnapshot.createSnapshot_text')
        if create_text and "successfully" in create_text.text and "created" not in progress_states:
            logger.info("    快照创建成功")
            progress_states.add("created")
        
        # 检查服务器启动状态
        start_text = page.ele('@id:vServerJob_KVMSnapshot.start_text')
        if start_text and "started" in start_text.text:
            logger.info("    服务器已启动")
            break
    
    logger.info(f"  快照 {snapshot_name} 创建完成")
    return snapshot_name

def cleanup_snapshots(page, keep_count):
    """清理旧快照 - 直接删除页面最上面的快照（最旧的）"""
    logger.info(f"  开始清理快照 (保留 {keep_count} 个)")
    
    # 等待并刷新页面
    time.sleep(40)
    page.ele('@id:sub_media_snapshot').click()
    time.sleep(20)
    
    # 获取所有快照行
    snapshot_rows = page.eles('xpath://table[@class="table table-striped"]//tbody/tr')
    all_snapshots = []
    
    for row in snapshot_rows:
        name_cell = row.ele('tag:td')
        if name_cell:
            snapshot_name = name_cell.text.strip()
            all_snapshots.append(snapshot_name)
    
    # 计算需要删除的快照数量
    total_count = len(all_snapshots)
    if total_count <= keep_count:
        logger.info("    无需删除，快照数量未超限")
        return
    
    # 需要删除的数量 = 总数 - 保留数量
    delete_count = total_count - keep_count
    
    logger.info(f"    需要删除 {delete_count} 个旧快照 (总共{total_count}个)")
    
    # 从最上面开始删除（最旧的）
    for i in range(delete_count):
        logger.info(f"    删除第 {i+1} 个旧快照")
        
        # 重新获取页面元素（因为删除操作会改变页面结构）
        snapshot_rows = page.eles('xpath://table[@class="table table-striped"]//tbody/tr')
        
        # 删除第一行（最上面的，最旧的）
        if snapshot_rows:
            first_row = snapshot_rows[0]
            name_cell = first_row.ele('tag:td')
            if name_cell:
                snapshot_name = name_cell.text.strip()
                logger.info(f"      删除快照: {snapshot_name}")
                
                # 查找并点击删除链接
                delete_link = first_row.ele('xpath:.//a[contains(@onclick, "delete")]')
                if delete_link:
                    delete_link.click()
                    time.sleep(1)
                    
                    # 确认删除
                    confirm_button = page.ele('@id:confirmationModalButton')
                    if confirm_button:
                        confirm_button.click()
                        time.sleep(20)  # 等待删除完成
                        logger.info(f"      删除成功")
                    else:
                        logger.warning(f"      删除失败: 未找到确认按钮")
                else:
                    logger.warning(f"      删除失败: 未找到删除按钮")
            else:
                logger.warning(f"      删除失败: 无法获取快照名称")
        else:
            logger.warning(f"      删除失败: 无法获取快照行")
    
    logger.info("  快照清理完成")

def process_server(page, server_config, current_index, total_count):
    """处理单个服务器的快照操作"""
    server_name = server_config['name']
    keep_count = server_config['snap_count']
    
    # 脱敏显示服务器名
    masked_name = mask_string(server_name, 3, 3)
    
    logger.info(f"[{current_index}/{total_count}] 处理服务器: {masked_name} (保留{keep_count}个快照)")
    
    try:
        # 选择服务器
        select_server(page, server_name)
        
        # 进入快照页面
        navigate_to_snapshots(page)
        
        # 获取当前快照信息
        current_count, existing_snapshots = get_snapshot_info(page)
        if current_count > 0:
            logger.info(f"  当前快照: {', '.join(existing_snapshots)}")
        
        # 创建新快照
        create_snapshot(page)
        
        # 判断是否需要清理
        future_count = current_count + 1
        if future_count > keep_count:
            cleanup_snapshots(page, keep_count)
        else:
            logger.info(f"  无需清理 (当前{future_count}个，限制{keep_count}个)")
        
        logger.info(f"服务器 {masked_name} 处理完成")
        return True
        
    except Exception as e:
        logger.error(f"服务器 {masked_name} 处理失败: {str(e)}")
        return False

def process_account(page, account_config, account_index, total_accounts):
    """处理单个账户"""
    username = account_config['username']
    servers = account_config['servers']
    
    # 脱敏显示用户名
    masked_username = mask_string(username, 2, 2)
    
    logger.info("=" * 60)
    logger.info(f"账户 {account_index}/{total_accounts}: {masked_username} ({len(servers)}个服务器)")
    logger.info("=" * 60)
    
    try:
        # 登录账户
        login_scp(page, username, account_config['password'])
        
        # 处理每个服务器
        success_count = 0
        for i, server_config in enumerate(servers, 1):
            if process_server(page, server_config, i, len(servers)):
                success_count += 1
            
            # 服务器间添加分隔
            if i < len(servers):
                logger.info("-" * 30)
        
        logger.info(f"账户 {masked_username} 完成: {success_count}/{len(servers)} 个服务器成功")
        return success_count, len(servers)
        
    except Exception as e:
        logger.error(f"账户 {masked_username} 处理失败: {str(e)}")
        return 0, len(servers)

def main():
    """主程序入口"""
    # 加载配置
    accounts = load_config()
    
    # 显示启动信息
    beijing_time = get_beijing_time()
    
    logger.info("NCSnap Start")
    logger.info(f"{beijing_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 初始化浏览器
    browser_options = setup_browser()
    page = ChromiumPage(browser_options)
    
    try:
        total_success = 0
        total_processed = 0
        
        # 处理每个账户
        for i, account in enumerate(accounts, 1):
            # 账户间切换
            if i > 1:
                logger.info("切换到下一个账户...")
                page.get('https://www.servercontrolpanel.de/SCP/Login')
                time.sleep(2)
            
            success, processed = process_account(page, account, i, len(accounts))
            total_success += success
            total_processed += processed
        
        # 显示最终结果
        end_time = get_beijing_time()
        logger.info("=" * 60)
        logger.info("任务完成")
        logger.info(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        sys.exit(1)
    
    finally:
        page.quit()
        logger.info("程序结束")

if __name__ == "__main__":
    main()
