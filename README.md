# NCSnap

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![GitHub Actions](https://img.shields.io/badge/github%20actions-automated-blue.svg)

**Netcup 自动创建快照并清理旧快照**

---

**联系方式**

[![Telegram](https://img.shields.io/badge/群聊-HeroCore-blue?logo=telegram&logoColor=white)](https://t.me/HeroCore) 
[![Telegram](https://img.shields.io/badge/频道-HeroMsg-blue?logo=telegram&logoColor=white)](https://t.me/HeroMsg)
[![Email](https://img.shields.io/badge/邮箱-联系我们-red?logo=gmail&logoColor=white)](mailto:admin@030101.xyz)

---

### 配置结构

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

### 推荐配置

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

使用旧格式时，所有服务器默认保留 3 个快照

### 混合格式

可以在同一账户内混合使用新旧格式：

```json
{
  "accounts": [
    {
      "username": "283861",
      "password": "password123",
      "servers": [
        {
          "name": "v2202505271811338415",
          "snap_count": 5
        },
        "v2202505271811343529"
      ]
    }
  ]
}
```

字符串格式的服务器会自动转换为对象格式，snap_count 默认为 3

---

[![Star History Chart](https://api.star-history.com/svg?repos=ymyuuu/NCSnap&type=Date)](https://star-history.com/#ymyuuu/NCSnap&Date)
