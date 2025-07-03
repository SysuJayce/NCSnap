#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# NetCup SCP 快照自动管理工具

from DrissionPage import ChromiumPage, ChromiumOptions
from datetime import datetime, timezone, timedelta
import time
import logging
import os
import sys

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

def get_config():
    """获取配置参数"""
    # 从环境变量读取配置
    nc_username = os.getenv('NC_USERNAME', '')
    nc_password = os.getenv('NC_PASSWORD', '')
    nc_servers = os.getenv('NC_SERVERS', '')
    snap_count = os.getenv('SNAP_COUNT', '1')
    
    # 显示原始环境变量值用于调试
    logger.info(f"环境变量 SNAP_COUNT 原始值: '{snap_count}'")
    
    # 验证必需参数
    if not nc_username or not nc_password:
        logger.error("缺少必需参数: NC_USERNAME 和 NC_PASSWORD")
        sys.exit(1)
    
    if not nc_servers:
        logger.error("缺少必需参数: NC_SERVERS")
        sys.exit(1)
    
    # 解析服务器列表
    servers = [s.strip() for s in nc_servers.split(',') if s.strip()]
    if not servers:
        logger.error("NC_SERVERS 格式错误，应为: server1,server2")
        sys.exit(1)
    
    # 解析保留快照数量
    try:
        keep_count = int(snap_count)
        if keep_count < 1:
            logger.warning("SNAP_COUNT 格式错误，使用默认值: 1")
            keep_count = 1
        else:
            logger.info(f"解析后的保留快照数量: {keep_count}")
    except ValueError:
        logger.warning(f"SNAP_COUNT 值 '{snap_count}' 无法转换为整数，使用默认值: 1")
        keep_count = 1
    
    return nc_username, nc_password, servers, keep_count

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
    
    logger.info("浏览器配置: 无头模式 + 无痕模式")
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
        logger.info(f"已跳转到: {current_url}")
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
    logger.info(f"设置保留数量: {keep_count}")
    
    # 按创建时间排序（最新的在最后）
    all_snapshots.sort()
    
    # 计算需要删除的快照
    if len(all_snapshots) <= keep_count:
        logger.info(f"快照数量 ({len(all_snapshots)}) 小于等于保留数量 ({keep_count})，无需删除")
        return
    
    # 保留最新的 keep_count 个，删除其余的
    snapshots_to_keep = all_snapshots[-keep_count:]  # 保留最后 N 个
    snapshots_to_delete = [s for s in all_snapshots if s not in snapshots_to_keep]
    
    if not snapshots_to_delete:
        logger.info("无快照需要删除")
        return
    
    logger.info(f"需要删除 {len(snapshots_to_delete)} 个旧快照")
    logger.info(f"将保留快照: {', '.join(snapshots_to_keep)}")
    logger.info(f"将删除快照: {', '.join(snapshots_to_delete)}")
    
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
        snapshot_name = create_snapshot(page)
        cleanup_old_snapshots(page, snapshot_name, keep_count)
        
        logger.info(f"服务器 {server_name} 处理完成")
        return True
        
    except Exception as e:
        logger.error(f"服务器 {server_name} 处理失败: {str(e)}")
        return False

def main():
    # 获取配置
    username, password, servers, keep_count = get_config()
    
    beijing_time = get_beijing_time()
    logger.info("NetCup SCP 快照自动管理工具启动")
    logger.info(f"当前北京时间: {beijing_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"目标服务器数量: {len(servers)}")
    logger.info(f"保留快照数量: {keep_count}")
    
    # 设置浏览器
    browser_options = setup_browser()
    page = ChromiumPage(browser_options)
    
    try:
        # 登录
        login_scp(page, username, password)
        
        # 处理每个服务器
        success_count = 0
        for i, server_name in enumerate(servers, 1):
            logger.info(f"处理进度: {i}/{len(servers)}")
            
            if process_server(page, server_name, keep_count):
                success_count += 1
        
        # 总结
        end_time = get_beijing_time()
        logger.info("=" * 50)
        logger.info("任务执行完成")
        logger.info(f"完成时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
        logger.info(f"成功处理: {success_count}/{len(servers)} 个服务器")
        if success_count < len(servers):
            logger.warning(f"失败数量: {len(servers) - success_count}")
        
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        sys.exit(1)
    
    finally:
        page.quit()
        logger.info("浏览器已关闭")

if __name__ == "__main__":
    main()
