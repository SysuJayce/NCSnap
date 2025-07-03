# NCSnap
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![GitHub Actions](https://img.shields.io/badge/github%20actions-automated-blue.svg)

**Netcup 自动创建快照并清理旧快照，默认每天北京时间早上 06:44 运行，可自行修改**

---

**联系方式**

[![Telegram](https://img.shields.io/badge/群聊-HeroCore-blue?logo=telegram&logoColor=white)](https://t.me/HeroCore) 
[![Telegram](https://img.shields.io/badge/频道-HeroMsg-blue?logo=telegram&logoColor=white)](https://t.me/HeroMsg)
[![Email](https://img.shields.io/badge/邮箱-联系我们-red?logo=gmail&logoColor=white)](mailto:admin@030101.xyz)

---

## 使用教程

### 1. 复刻项目

点击右上角的 `Fork` 按钮，复刻项目到你的GitHub账户。

### 2. 配置 Secrets

进入你复刻的仓库，点击 `Settings` → `Secrets and variables` → `Actions`，点击 `New repository secret`：

- **Name**: `NC_CONFIG`
- **Value**: 你的JSON配置内容（参考下方JSON配置说明）

### 3. 启用工作流

进入 `Actions` 页面，点击 `Enable workflows` 启用自动运行。

### 4. 测试运行

点击 `Run workflow` 手动运行一次，确保配置正确。

---

## JSON 配置说明

### 基本结构

```json
{
  "accounts": [
    {
      "username": "NetCup用户名",
      "password": "NetCup密码",
      "servers": [
        {
          "name": "服务器名称",
          "snap_count": "保留快照数量"
        }
      ]
    }
  ]
}
```

### 字段说明

- `accounts`: 账户数组，支持多个账户
- `username`: NetCup SCP 登录用户名（必填）
- `password`: NetCup SCP 登录密码（必填）
- `servers`: 服务器配置数组（必填）
- `name`: 服务器名称，在 SCP 面板显示的名称（必填）
- `snap_count`: 保留快照数量，不填默认为 3

### 多账户示例

```json
{
  "accounts": [
    {
      "username": "10010",
      "password": "password123",
      "servers": [
        {
          "name": "v2202505271811338445",
          "snap_count": 5
        },
        {
          "name": "v2202505271811343555",
          "snap_count": 3
        }
      ]
    },
    {
      "username": "10086",
      "password": "another_password",
      "servers": [
        {
          "name": "v2202505271811341234",
          "snap_count": 2
        }
      ]
    }
  ]
}
```

### 推荐格式

如果所有服务器保留相同数量快照，可以使用字符串数组：

```json
{
  "accounts": [
    {
      "username": "123456",
      "password": "password123",
      "servers": [
        "v2202505271811331234",
        "v2202505271811345678"
      ]
    }
  ]
}
```

使用简化格式时，所有服务器默认保留 3 个快照。

---

[![Star History Chart](https://api.star-history.com/svg?repos=ymyuuu/NCSnap&type=Date)](https://star-history.com/#ymyuuu/NCSnap&Date)
