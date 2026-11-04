# C3RB3R 勒索病毒 btrfs 数据恢复方案

针对 **Synology NAS（btrfs 文件系统）+ C3RB3R 勒索病毒（`.L0CK3D` 后缀）** 的完整数据恢复工具集与方法论。

> ⚠️ 本方案基于真实案例整理，仅供数据恢复用途。**恢复前请先做全盘镜像或确认可接受风险。**

## 核心结论（真实案例数据）

| 内容类型 | 恢复成功率 |
|---|---:|
| 照片原图（1–128 MB） | **97.9%** |
| 视频（1–128 MB） | **99.4%** |
| 大视频（>128 MB） | 80.8%（文件数） |
| 缩略图（<1 MB） | 约 55% |
| **总体（不含缩略图）** | **65.4%** |

### Drive 仓库挖掘（第五种路线）实测

| 块大小 | 成功率 |
|---|---:|
| 128–500 MB | 5.4% |
| **500–1000 MB** | **34.4%** |
| > 1 GB | 12% |


## 原理

C3RB3R 在文件尾部追加 588 字节 footer：

```
[0:48]   AES-256-CBC 包装的每文件 ChaCha8 密钥
[568:572] 会话标记
[572]     加密模式（0x24 / 0x25 / 0x26）
[573]     加密百分比
[574]     加密算法标记
[580:588] 原始文件长度 N（u64 LE）
```

**关键突破口**：btrfs 的写时复制（CoW）特性——文件被原地加密改写时，**原始数据块不会立即被覆盖**，只是不再被当前文件引用。因此可以通过 FIEMAP + delta 反推出原始 extent 的物理位置，直接读取原文。

## 五种恢复路线

| 方法 | 原理 | 成功率 | 适用 |
|---|---|---:|---|
| **A. CoW 反推** | FIEMAP 得当前物理位置，`delta = 物理 − 逻辑`，反推原 extent | 92–100% | 主力，所有模式 |
| **B. 旧根 bookend** | `btrfs-find-root` 找攻击前旧树，读旧 `EXTENT_DATA` | 30–60% | A 失败时补漏 |
| **C. 逐段拼接** | 0x25 三段布局，分别定位后拼接 | 63–89% | 大文件 |
| **D. 空闲空间雕刻** | 导出 free space tree，扫描 JPEG/PNG 头尾 | 48–55% | 缩略图 |
| **E. Drive 仓库挖掘** | 遍历 `@synologydrive/@sync/repo` 的加密块，按模式批量还原 + md5 去重 | 见下 | 有 Synology Drive 同步时 |

## 快速开始

```bash
# 1. 环境检查
python3 selfcheck.py

# 2. 配置（复制模板，填入你的 NAS 信息）
cp config.example.json config.json

# 3. 普查（只读，统计加密文件分布）
python3 nas_scripts/census_sizes.py /volume1/homes/USER/Photos

# 4. A 类恢复（主力方法）
python3 local_drivers/run_local_fast.py <base64后路径> <本地输出目录> <失败记录.tsv>

# 5. 大文件恢复
python3 local_drivers/run_big_multi.py <远端目录> <输出目录> <失败记录> 0 <进度文件> 0 2

# 6. 雕刻恢复（C 类）
python3 nas_scripts/carve_c.py     # 需要先生成 free.bin（见手册）
```

## 目录结构

```
nas_scripts/      NAS 端脚本（只读，需 root）
local_drivers/    本地驱动脚本（Windows/PowerShell + Python）
tools_windows/    辅助工具（SSH askpass 等）
AGENT_RUNBOOK.md  AI 代理执行手册
C3RB3R_btrfs_数据恢复手册.docx  完整技术手册
```

## 安全要求（重要）

1. **NAS 全程只读**——不写、不删、不改名、不做 balance/scrub/defrag
2. 使用 `O_NOATIME` 打开文件，避免元数据写入
3. 单流串行读取，避免磁头压力
4. 先做 SMART 与 `btrfs device stats` 健康检查
5. 恢复出的文件必须**完整解码校验**（ffmpeg / Pillow）
6. 解码失败的文件**单独保留，不要删除**

## 常见坑

| 坑 | 说明 |
|---|---|
| `-xerror` 太严 | 会误杀能播放的文件，建议宽松校验（能解码 3 秒即通过） |
| PowerShell 管道破坏二进制 | 用 `Start-Process -RedirectStandardOutput` |
| 并行分片共享临时文件 | 用每 PID 独立文件名 |
| 文件尾 footer 解析 | 注意 `N + 588 != 文件大小` 的情况 |
| 大文件不是越大越难 | 500–1000 MB 成功率最高（34%），>1 GB 仅 9.7% |

## 免责声明

本项目仅供**数据恢复与安全研究**使用。作者不对任何数据丢失或法律风险负责。请勿用于非法用途。

## License

MIT
