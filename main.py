#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# NetCup SCP 快照自动管理工具 - 支持多账户

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
        # 将记录的时间戳转换为北京时间
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
        
        # 验证每个账户的配置
        for i, account in enumerate(config['accounts']):
            required_fields = ['username', 'password', 'servers', 'snap_count']
            for field in required_fields:
                if field not in account:
                    logger.error(f"账户 {i+1} 缺少必需字段: {field}")
                    sys.exit(1)
            
            # 验证服务器列表
            if not isinstance(account['servers'], list) or len(account['servers']) == 0:
                logger.error(f"账户 {i+1} 的 servers 必须是非空数组")
                sys.exit(1)
            
            # 验证快照数量
            if not isinstance(account['snap_count'], int) or account['snap_count'] < 1:
                logger.error(f"账户 {i+1} 的 snap_count 必须是正整数")
                sys.exit(1)
        
        return config['accounts']
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON配置文件格式错误: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"读取配置文件失败: {str(e)}")
        sys.exit(1)

def setup_browser():
    """设置和配置浏览器选项"""
    co = ChromiumOptions()
    
    # 启用无头模式，不显示浏览器界面
    co.headless()
    
    # 启用无痕模式，不保存浏览数据
    co.incognito()
    
    # 添加其他优化参数以提高性能和稳定性
    co.set_argument('--no-sandbox')  # 禁用沙盒模式
    co.set_argument('--disable-dev-shm-usage')  # 禁用/dev/shm使用
    co.set_argument('--disable-gpu')  # 禁用GPU加速
    co.set_argument('--disable-extensions')  # 禁用扩展
    co.set_argument('--window-size=1920,1080')  # 设置窗口大小
    
    # 禁用图片加载以提高页面加载速度
    co.no_imgs(True)
    return co

def login_scp(page, username, password):
    """登录NetCup SCP管理面板"""
    logger.info("开始登录NetCup SCP面板")
    
    # 访问登录页面
    page.get('https://www.servercontrolpanel.de/SCP/Login')
    page.ele('@name:username')  # 等待用户名输入框加载
    time.sleep(2)
    
    # 输入登录凭据
    page.ele('@name:username').input(username)  # 输入用户名
    page.ele('@name:password').input(password)  # 输入密码
    page.ele('@type:submit').click()  # 点击登录按钮
    
    logger.info("登录请求已发送，验证账号密码...")
    time.sleep(3)
    
    # 检查登录结果
    current_url = page.url
    if '/Login' in current_url:
        # 如果仍在登录页面，说明登录失败
        logger.error("登录失败: 账号或密码错误")
        logger.error(f"当前页面: {current_url}")
        raise Exception("账号或密码错误，登录失败")
    elif '/Home' in current_url:
        # 成功跳转到首页
        logger.info("登录成功")
        return True
    else:
        # 其他情况，可能登录成功但跳转到其他页面
        logger.warning(f"未知页面状态: {current_url}")
        return True

def select_server(page, server_name):
    """选择指定的服务器"""
    logger.info(f"选择服务器: {server_name}")
    
    # 等待服务器选择器加载
    page.ele('@id:navSelect')
    time.sleep(2)
    
    # 点击下拉菜单按钮
    select_button = page.ele('css:.btn.dropdown-toggle')
    select_button.click()
    time.sleep(1)
    
    # 在搜索框中输入服务器名称进行筛选
    search_box = page.ele('css:.bs-searchbox input')
    search_box.input(server_name)
    time.sleep(1)
    
    # 点击匹配的服务器选项
    server_link = page.ele(f'xpath://a[contains(.//span, "{server_name}")]')
    server_link.click()
    
    logger.info("服务器选择完成")

def navigate_to_snapshots(page):
    """导航到快照管理页面"""
    logger.info("导航到快照管理页面")
    
    # 点击Media菜单项
    page.ele('@id:vServerpane_media')
    time.sleep(2)
    page.ele('@id:vServerpane_media').click()
    
    # 点击Snapshots子菜单项
    page.ele('@id:sub_media_snapshot')
    time.sleep(2)
    page.ele('@id:sub_media_snapshot').click()
    
    # 等待快照页面加载完成
    page.ele('@id:snapshotName')
    time.sleep(2)
    
    logger.info("已进入快照管理页面")

def get_current_snapshot_count(page):
    """获取当前快照数量"""
    try:
        # 查找快照表格中的所有行
        snapshot_rows = page.eles('xpath://table[@class="table table-striped"]//tbody/tr')
        
        # 过滤出有效的快照行（排除空行和标题行）
        valid_snapshots = []
        for row in snapshot_rows:
            name_cell = row.ele('tag:td')
            if name_cell and name_cell.text.strip():
                valid_snapshots.append(name_cell.text.strip())
        
        count = len(valid_snapshots)
        logger.info(f"当前快照数量: {count}")
        if count > 0:
            logger.info(f"现有快照: {', '.join(valid_snapshots)}")
        
        return count, valid_snapshots
        
    except Exception as e:
        logger.warning(f"获取快照数量失败: {str(e)}")
        return 0, []

def create_snapshot(page):
    """创建新的快照"""
    # 使用北京时间生成快照名称
    beijing_time = get_beijing_time()
    snapshot_name = beijing_time.strftime("%Y%m%d%H%M%S")
    logger.info(f"开始创建快照: {snapshot_name} (北京时间: {beijing_time.strftime('%Y-%m-%d %H:%M:%S')})")
    
    # 填写快照信息
    page.ele('@id:snapshotName').input(snapshot_name)  # 输入快照名称
    page.ele('@id:snapshotDescription').input("Auto snapshot")  # 输入快照描述
    page.ele('xpath://a[contains(@onclick, "sendCreateSnapshotForm")]').click()  # 点击创建按钮
    
    # 监控快照创建进度
    printed_states = set()  # 记录已打印的状态，避免重复输出
    
    while True:
        time.sleep(1)
        
        # 检查服务器停止状态
        stop_text = page.ele('@id:vServerJob_KVMSnapshot.stop_text')
        if stop_text and "stopped" in stop_text.text and "stopped" not in printed_states:
            logger.info("└── 服务器已停止")
            printed_states.add("stopped")
        
        # 检查快照创建状态
        create_text = page.ele('@id:vServerJob_KVMSnapshot.createSnapshot_text') 
        if create_text and "successfully" in create_text.text and "created" not in printed_states:
            logger.info("└── 快照创建成功")
            printed_states.add("created")
            
        # 检查服务器启动状态
        start_text = page.ele('@id:vServerJob_KVMSnapshot.start_text')
        if start_text and "started" in start_text.text:
            logger.info("└── 服务器已启动")
            break
    
    logger.info(f"快照 {snapshot_name} 创建完成")
    return snapshot_name

def cleanup_old_snapshots(page, current_snapshot, keep_count):
    """清理旧快照，保留指定数量的最新快照"""
    logger.info(f"开始清理旧快照 (保留最新 {keep_count} 个)")
    
    # 等待快照创建完全完成，然后刷新页面
    time.sleep(40)
    page.ele('@id:sub_media_snapshot').click()
    time.sleep(20)
    
    # 收集所有快照信息（按创建时间排序，最新的在最下面）
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
    
    # 逐个删除旧快照
    for i, snapshot_to_delete in enumerate(snapshots_to_delete, 1):
        logger.info(f"删除快照 ({i}/{len(snapshots_to_delete)}): {snapshot_to_delete}")
        
        # 重新获取页面上的快照行（因为删除操作会改变页面结构）
        snapshot_rows = page.eles('xpath://table[@class="table table-striped"]//tbody/tr')
        
        # 查找要删除的快照行
        target_row = None
        for row in snapshot_rows:
            name_cell = row.ele('tag:td')
            if name_cell and name_cell.text.strip() == snapshot_to_delete:
                target_row = row
                break
        
        if target_row:
            # 点击删除链接
            delete_link = target_row.ele('xpath:.//a[contains(@onclick, "delete")]')
            if delete_link:
                delete_link.click()
                time.sleep(1)
                
                # 确认删除操作
                confirm_button = page.ele('@id:confirmationModalButton')
                if confirm_button:
                    confirm_button.click()
                    time.sleep(20)  # 等待删除完成
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
        # 选择服务器并导航到快照页面
        select_server(page, server_name)
        navigate_to_snapshots(page)
        
        # 获取当前快照数量，用于智能判断是否需要清理
        current_count, existing_snapshots = get_current_snapshot_count(page)
        
        # 创建新快照
        snapshot_name = create_snapshot(page)
        
        # 智能判断是否需要清理：如果创建后总数超过限制才进行清理
        future_count = current_count + 1  # 加上刚创建的快照
        if future_count > keep_count:
            logger.info(f"创建后将有 {future_count} 个快照，超过限制 {keep_count}，需要清理")
            cleanup_old_snapshots(page, snapshot_name, keep_count)
        else:
            logger.info(f"创建后将有 {future_count} 个快照，未超过限制 {keep_count}，无需清理")
        
        logger.info(f"服务器 {server_name} 处理完成")
        return True
        
    except Exception as e:
        logger.error(f"服务器 {server_name} 处理失败: {str(e)}")
        return False

def process_account(page, account, account_index, total_accounts):
    """处理单个账户下的所有服务器"""
    logger.info("=" * 60)
    logger.info(f"开始处理账户 {account_index}/{total_accounts}")
    logger.info(f"用户名: {account['username']}")
    logger.info(f"服务器数量: {len(account['servers'])}")
    logger.info(f"保留快照数量: {account['snap_count']}")
    logger.info("=" * 60)
    
    try:
        # 登录账户
        login_scp(page, account['username'], account['password'])
        
        # 处理该账户下的每个服务器
        success_count = 0
        for i, server_name in enumerate(account['servers'], 1):
            logger.info(f"账户 {account_index} 服务器进度: {i}/{len(account['servers'])}")
            
            if process_server(page, server_name, account['snap_count']):
                success_count += 1
        
        logger.info(f"账户 {account_index} 处理完成: {success_count}/{len(account['servers'])} 个服务器成功")
        return success_count, len(account['servers'])
        
    except Exception as e:
        logger.error(f"账户 {account_index} 处理失败: {str(e)}")
        return 0, len(account['servers'])

def main():
    """主程序入口"""
    # 加载配置文件
    accounts = load_config()
    
    # 显示程序启动信息
    beijing_time = get_beijing_time()
    logger.info("NCSnap Go - 多账户版本")
    logger.info(f"启动时间: {beijing_time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    logger.info(f"配置账户数量: {len(accounts)}")
    
    # 计算总服务器数量
    total_servers = sum(len(account['servers']) for account in accounts)
    logger.info(f"总服务器数量: {total_servers}")
    
    # 设置浏览器
    browser_options = setup_browser()
    page = ChromiumPage(browser_options)
    
    try:
        # 处理每个账户
        total_success = 0
        total_servers_processed = 0
        
        for i, account in enumerate(accounts, 1):
            # 处理完一个账户后，直接跳转到登录页面处理下一个账户
            if i > 1:
                logger.info("准备处理下一个账户...")
                page.get('https://www.servercontrolpanel.de/SCP/Login')
                time.sleep(2)
            
            success_count, server_count = process_account(page, account, i, len(accounts))
            total_success += success_count
            total_servers_processed += server_count
        
        # 显示最终统计信息
        end_time = get_beijing_time()
        logger.info("=" * 60)
        logger.info("所有任务执行完成")
        logger.info(f"完成时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
        logger.info(f"处理账户: {len(accounts)} 个")
        logger.info(f"成功处理服务器: {total_success}/{total_servers_processed} 个")
        
        # if total_success < total_servers_processed:
        #     logger.warning(f"失败服务器数量: {total_servers_processed - total_success}")
        
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        sys.exit(1)
    
    finally:
        # 关闭浏览器并清理资源
        page.quit()
        logger.info("浏览器已关闭，程序结束")

if __name__ == "__main__":
    main()
