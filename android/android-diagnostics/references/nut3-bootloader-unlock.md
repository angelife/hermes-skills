# 坚果3 (DT1902A) Bootloader 解锁 + Magisk

## 背景：锤子不开放解锁

Smartisan/锤子科技从未提供过官方 bootloader 解锁通道。标准方法均失效：

```bash
# ❌ 需要 unlocktoken，锤子没给过
fastboot flashing unlock
# FAILED (remote: 'Unlock is not allowed without unlocktoken authority')

# ❌ 不支持
fastboot oem unlock
# FAILED (remote: 'unknown command')

# ❌ 不支持
fastboot oem device-id
# FAILED (remote: 'unknown command')
```

**设备信息：**
- `product:msmnile`（骁龙 855 / SM8150）
- `variant:SDM UFS`（UFS 存储）
- `kernel:uefi`（UEFI 启动）
- A/B 分区系统，current-slot:a
- `unlocked:no, secure:yes`

## 唯一可行路线：高通 9008 EDL 模式

### 前置条件
- **EDL 线（工程线/9008 线）** — 淘宝十几块一根，Type-C 接口。部分商家标"小米工程线"，通用。
- **QPST/QFIL 工具** — 高通线刷工具
- **TWRP 线刷包** — 需要从 Nut3 相关资源获取
- 注意：不建议 DIY Type-C 的 EDL 线（焊接复杂），直接买最省事。

### 流程概要
1. 关机，彻底断电（屏幕不亮）
2. EDL 线插电脑，按住线控开关，插入手机，等待约 3 秒松手
3. QFIL 识别到 `Qualcomm HS-USB QDLoader 9008` 端口
4. QFIL → Flat Build → 选择 Programmer（prog_ 开头）→ Load XML（rawprogram_unsparse.xml）→ Download
5. 刷入 TWRP
6. 长按音量增+电源进入 TWRP
7. 在 TWRP 中刷 Magisk 或其他 ROM

### Magisk 兼容性

| 版本 | 状态 | 原因 |
|------|------|------|
| v19.3 | ✅ 可用 | 签名与 Smartisan BL 兼容 |
| v20+ | ❌ 不可用 | boot.img 签名校验不通过，刷了会卡白锤子 |

Smartisan 的 locked bootloader 会校验 boot.img 签名。Magisk v19.3 使用了一种与 Smartisan 兼容的签名策略，v20+ 改了签名方式后就不行了。

### 注意事项
- 即使成功刷入 Magisk，Smartisan 的 bootloader 仍处于 locked 状态，会持续校验签名。任何修改 boot 分区后签名不匹配的操作都可能导致卡锤子 logo。
- 如果刷回了 Smartisan 原厂 ROM 或有 OTA 更新，Magisk 会被覆盖，需要重新刷。
- 刷入非官方 ROM（如魔趣/MoKee）后，Smartisan 原厂功能（大爆炸/一步/闪念胶囊）会失效。

## 参考来源
- [坚果3刷魔趣体验 — iminto.github.io](https://iminto.github.io/post/%E5%9D%9A%E6%9E%9C3%E6%89%8B%E6%9C%BA%E5%88%B7%E9%AD%94%E8%B6%A3%E4%BD%93%E9%AA%8C/)
- [坚果3刷机指南 — mintimate.cn](https://www.mintimate.cn/2019/11/30/%E5%9D%9A%E6%9E%9C3%E5%88%B7%E9%AD%94%E8%B6%A3/)
