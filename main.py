#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# NetCup SCP 多账户快照自动管理工具

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
        dt = datetime.fromtimestamp(record.created, tz=BEIJING_TZ)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime('%H:%M:%S')

# 配置日志
handler = logging.StreamHandler()
handler.setFormatter(BeijingFormatter(
    fmt='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

def get_beijing_time():
    """获取北京时间"""
    return datetime.now(tz=BEIJING_TZ)

def load_config():
    """从JSON文件加载配置"""
    config_file = 'config.json'
    
    if not os.path.exists(config_file):
        logger.error(f"配置文件 {config_file} 不存在")
        sys.exit(1)
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"配置文件格式错误: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")
        sys.exit(1)
    
    # 验证配置格式
    if 'accounts' not in config:
        logger.error("配置文件缺少 'accounts' 字段")
        sys.exit(1)
    
    if not config['accounts']:
        logger.error("accounts 数组为空")
        sys.exit(1)
    
    # 验证每个账户配置
    for i, account in enumerate(config['accounts']):
        required_fields = ['username', 'password', 'servers', 'snap_count']
        for field in required_fields:
            if field not in account:
                logger.error(f"第 {i+1} 个账户缺少必需字段: {field}")
                sys.exit(1)
        
        if not account['servers']:
            logger.error(f"第 {i+1} 个账户的服务器列表为空")
            sys.exit(1)
        
        if not isinstance(account['snap_count'], int) or account['snap_count'] < 1:
            logger.error(f"第 {i+1} 个账户的 snap_count 必须是大于0的整数")
            sys.exit(1)
    
    return config['accounts']

def setup_browser():
    """设置浏览器选项"""
    co = ChromiumOptions()
    
    # 无头模式
    co.headless()
    
    # 无痕模式  
    co.incognito()
    
    # 其他优化设置
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-extensions')
    co.set_argument('--window-size=1920,1080')
    
    # 禁用图片加载以提高速度
    co.no_imgs(True)
    return co

def login_scp(page, username, password):
    """登录SCP面板"""
    logger.info("开始登录NetCup SCP面板")
    
    page.get('https://www.servercontrolpanel.de/SCP/Login')
    page.ele('@name:username')
    time.sleep(2)
    
    page.ele('@name:username').input(username)
    page.ele('@name:password').input(password)
    page.ele('@type:submit').click()
    
    logger.info("登录请求已发送，验证账号密码...")
    time.sleep(3)
    
    # 检查登录结果
    current_url = page.url
    if '/Login' in current_url:
        logger.error("登录失败: 账号或密码错误")
        logger.error(f"当前页面: {current_url}")
        raise Exception("账号或密码错误，登录失败")
    elif '/Home' in current_url:
        logger.info("登录成功")
        return True
    else:
        logger.warning(f"未知页面状态: {current_url}")
        return True

def select_server(page, server_name):
    """选择指定服务器"""
    logger.info(f"选择服务器: {server_name}")
    
    page.ele('@id:navSelect')
    time.sleep(2)
    
    select_button = page.ele('css:.btn.dropdown-toggle')
    select_button.click()
    time.sleep(1)
    
    search_box = page.ele('css:.bs-searchbox input')
    search_box.input(server_name)
    time.sleep(1)
    
    server_link = page.ele(f'xpath://a[contains(.//span, "{server_name}")]')
    server_link.click()
    
    logger.info("服务器选择完成")

def navigate_to_snapshots(page):
    """导航到快照页面"""
    logger.info("导航到快照管理页面")
    
    # 进入Media
    page.ele('@id:vServerpane_media')
    time.sleep(2)
    page.ele('@id:vServerpane_media').click()
    
    # 进入Snapshots
    page.ele('@id:sub_media_snapshot')
    time.sleep(2)
    page.ele('@id:sub_media_snapshot').click()
    
    page.ele('@id:snapshotName')
    time.sleep(2)
    
    logger.info("已进入快照管理页面")

def get_current_snapshot_count(page):
    """获取当前快照数量"""
    snapshot_rows = page.eles('xpath://table[@class="table table-striped"]//tbody/tr')
    current_count = len(snapshot_rows)
    logger.info(f"当前快照数量: {current_count}")
    return current_count

def create_snapshot(page):
    """创建新快照"""
    # 使用北京时间生成快照名称
    beijing_time = get_beijing_time()
    snapshot_name = beijing_time.strftime("%Y%m%d%H%M%S")
    logger.info(f"开始创建快照: {snapshot_name} (北京时间: {beijing_time.strftime('%Y-%m-%d %H:%M:%S')})")
    
    page.ele('@id:snapshotName').input(snapshot_name)
    page.ele('@id:snapshotDescription').input("Auto snapshot")
    page.ele('xpath://a[contains(@onclick, "sendCreateSnapshotForm")]').click()
    
    # 监控快照创建进度
    printed_states = set()
    
    while True:
        time.sleep(1)
        
        stop_text = page.ele('@id:vServerJob_KVMSnapshot.stop_text')
        if stop_text and "stopped" in stop_text.text and "stopped" not in printed_states:
            logger.info("└── 服务器已停止")
            printed_states.add("stopped")
        
        create_text = page.ele('@id:vServerJob_KVMSnapshot.createSnapshot_text') 
        if create_text and "successfully" in create_text.text and "created" not in printed_states:
            logger.info("└── 快照创建成功")
            printed_states.add("created")
            
        start_text = page.ele('@id:vServerJob_KVMSnapshot.start_text')
        if start_text and "started" in start_text.text:
            logger.info("└── 服务器已启动")
            break
    
    logger.info(f"快照 {snapshot_name} 创建完成")
    return snapshot_name

def cleanup_old_snapshots(page, current_snapshot, keep_count):
    """清理旧快照，保留指定数量"""
    logger.info(f"开始清理旧快照 (保留最新 {keep_count} 个)")
    
    time.sleep(40)
    page.ele('@id:sub_media_snapshot').click()
    time.sleep(20)
    
    # 收集所有快照（按创建时间排序，最新的在最下面）
    snapshot_rows = page.eles('xpath://table[@class="table table-striped"]//tbody/tr')
    all_snapshots = []
    
    for row in snapshot_rows:
        name_cell = row.ele('tag:td')
        if name_cell:
            snapshot_name = name_cell.text.strip()
            all_snapshots.append(snapshot_name)
    
    logger.info(f"当前共有 {len(all_snapshots)} 个快照")
    
    # 按创建时间排序（最新的在最后）
    all_snapshots.sort()
    
    # 计算需要删除的快照
    if len(all_snapshots) <= keep_count:
        logger.info("无需删除快照，数量未超过限制")
        return
    
    # 保留最新的 keep_count 个，删除其余的
    snapshots_to_keep = all_snapshots[-keep_count:]  # 保留最后 N 个
    snapshots_to_delete = [s for s in all_snapshots if s not in snapshots_to_keep]
    
    if not snapshots_to_delete:
        logger.info("无快照需要删除")
        return
    
    logger.info(f"需要删除 {len(snapshots_to_delete)} 个旧快照")
    logger.info(f"保留快照: {', '.join(snapshots_to_keep)}")
    
    # 逐个删除
    for i, snapshot_to_delete in enumerate(snapshots_to_delete, 1):
        logger.info(f"删除快照 ({i}/{len(snapshots_to_delete)}): {snapshot_to_delete}")
        
        snapshot_rows = page.eles('xpath://table[@class="table table-striped"]//tbody/tr')
        
        target_row = None
        for row in snapshot_rows:
            name_cell = row.ele('tag:td')
            if name_cell and name_cell.text.strip() == snapshot_to_delete:
                target_row = row
                break
        
        if target_row:
            delete_link = target_row.ele('xpath:.//a[contains(@onclick, "delete")]')
            if delete_link:
                delete_link.click()
                time.sleep(1)
                
                confirm_button = page.ele('@id:confirmationModalButton')
                if confirm_button:
                    confirm_button.click()
                    time.sleep(20)
                    logger.info(f"└── {snapshot_to_delete} 删除成功")
                else:
                    logger.warning(f"└── {snapshot_to_delete} 删除失败: 未找到确认按钮")
            else:
                logger.warning(f"└── {snapshot_to_delete} 删除失败: 未找到删除按钮")
        else:
            logger.warning(f"└── {snapshot_to_delete} 删除失败: 未找到快照")
    
    logger.info("快照清理完成")

def process_server(page, server_name, keep_count):
    """处理单个服务器的快照操作"""
    logger.info(f"=" * 50)
    logger.info(f"开始处理服务器: {server_name}")
    logger.info(f"=" * 50)
    
    try:
        select_server(page, server_name)
        navigate_to_snapshots(page)
        
        # 获取当前快照数量
        current_count = get_current_snapshot_count(page)
        
        # 判断创建快照后是否需要删除
        will_need_cleanup = (current_count + 1) > keep_count
        
        if will_need_cleanup:
            logger.info(f"创建快照后将有 {current_count + 1} 个快照，超过限制 {keep_count} 个，需要清理")
        else:
            logger.info(f"创建快照后将有 {current_count + 1} 个快照，未超过限制 {keep_count} 个，无需清理")
        
        # 创建快照
        snapshot_name = create_snapshot(page)
        
        # 根据预判结果决定是否执行清理
        if will_need_cleanup:
            cleanup_old_snapshots(page, snapshot_name, keep_count)
        else:
            logger.info("跳过快照清理，节省等待时间")
        
        logger.info(f"服务器 {server_name} 处理完成")
        return True
        
    except Exception as e:
        logger.error(f"服务器 {server_name} 处理失败: {str(e)}")
        return False

def process_account(page, account, account_index, total_accounts):
    """处理单个账户"""
    username = account['username']
    servers = account['servers']
    keep_count = account['snap_count']
    
    logger.info(f"{'=' * 60}")
    logger.info(f"开始处理账户 {account_index}/{total_accounts}: {username}")
    logger.info(f"服务器数量: {len(servers)}, 保留快照数量: {keep_count}")
    logger.info(f"{'=' * 60}")
    
    try:
        # 登录账户
        login_scp(page, username, account['password'])
        
        # 处理该账户下的所有服务器
        success_count = 0
        for i, server_name in enumerate(servers, 1):
            logger.info(f"账户 {account_index} 服务器进度: {i}/{len(servers)}")
            
            if process_server(page, server_name, keep_count):
                success_count += 1
        
        logger.info(f"账户 {username} 处理完成，成功: {success_count}/{len(servers)}")
        return success_count, len(servers)
        
    except Exception as e:
        logger.error(f"账户 {username} 处理失败: {str(e)}")
        return 0, len(servers)

def main():
    # 加载配置
    accounts = load_config()
    
    beijing_time = get_beijing_time()
    logger.info("NCSnap Go - 多账户版本")
    logger.info(f"{beijing_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"配置的账户数量: {len(accounts)}")
    
    total_servers = sum(len(account['servers']) for account in accounts)
    logger.info(f"总服务器数量: {total_servers}")
    
    # 设置浏览器
    browser_options = setup_browser()
    page = ChromiumPage(browser_options)
    
    try:
        total_success = 0
        total_servers_processed = 0
        
        # 处理每个账户
        for i, account in enumerate(accounts, 1):
            success_count, server_count = process_account(page, account, i, len(accounts))
            total_success += success_count
            total_servers_processed += server_count
        
        # 总结
        end_time = get_beijing_time()
        logger.info("=" * 60)
        logger.info("所有任务执行完成")
        logger.info(f"完成时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
        logger.info(f"处理账户: {len(accounts)} 个")
        logger.info(f"成功处理服务器: {total_success}/{total_servers_processed} 个")
        if total_success < total_servers_processed:
            logger.warning(f"失败数量: {total_servers_processed - total_success}")
        
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        sys.exit(1)
    
    finally:
        page.quit()
        logger.info("浏览器已关闭")

if __name__ == "__main__":
    main()
