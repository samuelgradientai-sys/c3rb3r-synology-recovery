# C3RB3R 数据恢复任务 · AI 执行手册（Agent Runbook）

> 本文件是给 AI Agent 直接执行的作业指导书。人类读者请先看 `C3RB3R_btrfs_数据恢复手册.docx`。
> 你的目标：在**只读源盘**的前提下，把 C3RB3R（.L0CK3D）加密的文件尽可能多地恢复出来，并给出可核验的统计。

---

## 0. 角色与总目标

你是一名数据恢复工程师。给定：

- 一台装有 btrfs 卷的源端（NAS/Linux），上面有被 C3RB3R 加密的文件（后缀 `.L0CK3D`）
- 一台操作端（Windows/Linux），有本地磁盘用于落地

你要按 **调研 → A 类 → bookend → B 类 → C 类 → 清单统计** 的顺序推进，每个阶段都有明确的成功判据和失败分支。

**最终交付**：
1. 恢复出来的文件（按原始目录结构存放）
2. 失败清单（CSV/文档，每条含路径+原因）
3. 统计报告（按类别、按大小/类型的成功率）

---

## 1. 硬约束（违反即任务失败）

1. **绝不写源盘**：不创建、不删除、不改名、不改权限、不 touch、不写入任何字节。
2. **绝不运行**：`btrfs balance`、`btrfs scrub`、`btrfs defrag`、`btrfs subvolume delete`、`btrfs check --repair`、`fsck`。
3. **绝不在源卷上落地**：恢复产物必须写到另一块盘。
4. **所有读文件操作必须带 `O_NOATIME`**（Python：`os.open(p, os.O_RDONLY | 0o40000)`），否则会更新 atime 产生元数据写入，既慢又破坏现场。
5. **不确定是否只读的命令，不要执行**；先问。
6. 恢复产物必须逐文件做完整解码校验（ffmpeg / Pillow），校验不过的**不算成功**。

---

## 2. 开工前的环境自检（必须全部通过）

| 检查项 | 命令 | 通过标准 |
|---|---|---|
| 源端 root | `sudo -n true` 或能提权 | 能执行 `btrfs` 命令 |
| btrfs 工具 | `which btrfs btrfs-debug-tree btrfs-find-root btrfs-map-logical` | 4 个都在 |
| 文件系统 | `btrfs filesystem show <DEV>` | 正常输出 |
| CoW 开启 | `lsattr -d <SHARE>/*` | 没有 `C` 标志 |
| 源端 Python | `python3 -V` | ≥ 3.8 |
| 操作端 Python | `python -V` | ≥ 3.8，且有 Pillow |
| ffmpeg | `<FFMPEG> -version` | 能运行 |
| 落地空间 | 各盘剩余 | 目标目录 ≥ 加密总量的 1.2 倍；C 盘保留 ≥ 20 GB |

把结果记到 `state.json`，任何一项失败 → 停下并报告，不要猜。

---

## 3. 配置文件（先填这个）

把 `config.example.json` 复制成 `config.json` 并填好：

```json
{
  "dev": "/dev/mapper/cachedev_0",
  "share": "/volume1/homes/<user>/Photos",
  "out_root": "F:\\恢复数据_<user>",
  "work_dir": "F:\\work",
  "ffmpeg": "E:\\...\\ffmpeg.exe",
  "ssh": {"host": "<ip>", "user": "<user>", "port": 22,
           "askpass": "%TEMP%\\askpass.exe"},
  "min_free_gb": {"C": 20, "D": 5, "E": 5, "F": 5}
}
```

后续所有命令中的 `<DEV>` `<SHARE>` `<OUT>` `<WORK>` `<FFMPEG>` 都用这里替换。

---

## 4. 阶段机（严格按序，不可跳步）

每个阶段结构固定：**前置条件 → 命令 → 成功判据 → 失败分支 → 记录**。

### 阶段 0：普查

- 前置：环境自检全过
- 命令：
  ```bash
  python3 nas_scripts/census_photos.py <SHARE>
  python3 nas_scripts/census_sizes.py <base64(<SHARE>)>
  ```
- 成功判据：拿到文件数、模式分布（0x24/0x25/0x26）、总字节数
- 失败分支：
  - 若 0x25+0x26 占比 = 0 → 全是 0x24，直接跳阶段 3（C 类）
  - 若文件数为 0 → 路径错或没权限，回查
- 记录：写 `state.json` → `{"phase":0, "counts": {...}}`

### 阶段 1：A 类（0x25/0x26，≤128 MiB）

- 前置：阶段 0 拿到 A 类数量 > 0；落地盘空间足够
- 命令：
  ```bash
  python local_drivers/run_local_fast.py <SHARE> <OUT> <WORK>/fail_A.tsv
  ```
- 成功判据：**文件成功率 ≥ 85%**
- 失败分支：
  - 60–85% → 正常，继续，失败交给阶段 2
  - < 60% → **停止并报告**（可能原因：CoW 未开、卷被大量写过、base 选错）
- 记录：`{"phase":1, "ok": n, "skip": {...}}`

### 阶段 2：旧根 bookend（补 A 类失败）

- 前置：阶段 1 有失败文件；失败清单已生成
- 命令：
  ```bash
  btrfs-find-root -a <DEV> > <WORK>/findroot.txt
  python3 nas_scripts/resolve262.py <候选块1> <候选块2> ...
  python local_drivers/run_bookend.py <WORK>/fail_list.txt <OUT> \
         <WORK>/bk_prog.txt <WORK>/bk_fail.tsv <SHARE>/
  ```
- 成功判据：**命中率 ≥ 25%**
- 失败分支：
  - 前 200 个文件命中 0 → 旧根已失效，**放弃本阶段**，记录原因
  - 命中 25–50% → 正常
  - 单个文件报 `no-valid-extent` / `stat-failed` → 正常跳过，不重试超过 2 次
- 记录：`{"phase":2, "ok": n, "no_valid": n}`

### 阶段 3：B 类（> 128 MiB 大视频）

- 前置：阶段 0 显示存在 >128 MiB 文件
- 命令（分片并行，n=2~4；注意每个分片必须用独立的远端临时文件名）：
  ```bash
  python local_drivers/run_big_multi.py <SHARE> <OUT> <WORK>/fail_B.tsv 0 \
         <WORK>/prog.txt <k> <n>
  ```
- 成功判据：文件成功率 ≥ 50%
- 失败分支：< 30% → 记录并继续（大文件天生难），不要死磕
- 记录：`{"phase":3, "ok": n, "skip": n}`

### 阶段 4：C 类（0x24 小文件，空闲空间雕刻）

- 前置：A/B/bookend 都已完成（C 类最慢、价值最低，最后做）
- 子步骤：
  1. 导出空闲空间树并转区间
     ```bash
     btrfs-debug-tree -t 10 <DEV> > <WORK>/free_tree.txt
     python3 nas_scripts/parse_free_space.py <WORK>/free_tree.txt <WORK>/free.json
     python3 nas_scripts/make_ranges.py <WORK>/free.json <WORK>/ranges.txt
     ```
  2. 列出 0x24 清单（路径 + 原始长度）
     ```bash
     python3 nas_scripts/list_024.py <base64(<SHARE>)> > <WORK>/list_024.tsv
     ```
  3. 流式导出空闲空间镜像（**必须放 SSD**，并确认 `zero-filled` 计数）
     ```bash
     ssh <host> "sudo python3 /tmp/raw_reader2.py" > <WORK>/free.bin
     ```
     校验：`发送字节数 - 帧头总长 == free.bin 实际大小`；不等则**禁止继续**（会出“错图”）
  4. 雕刻 + 匹配
     ```bash
     python3 nas_scripts/carve_c.py
     python3 nas_scripts/match_c.py
     ```
- 成功判据：匹配率 ≥ 35%，且**候选目录全部可解码**
- 失败分支：
  - 匹配 < 10% → 检查 list 的路径前缀与 free.bin 的帧对齐
  - 出现 `verify_fail` 大量增加 → 可能是镜像过期（卷已被写过），记录并停
- 记录：`{"phase":4, "certain": n, "maybe": n, "missing": n}`

### 阶段 5：清单与统计

- 命令：
  ```bash
  python local_drivers/make_fail_docx_all.py
  python local_drivers/make_size_xlsx.py
  ```
- 成功判据：CSV 行数 = 各类失败之和；Excel 的“合计”与磁盘实际文件数能对上
- **失败清单必须从磁盘反查生成**（恢复目录里没有该文件才算失败），不要用日志行数

---

## 5. 决策阈值总表

| 指标 | 正常区间 | 低于下限的动作 |
|---|---|---|
| A 类文件成功率 | 90–100% | < 60% 停止并报告 |
| bookend 命中率 | 25–60% | 前 200 个为 0 则放弃 |
| B 类文件成功率 | 50–85% | < 30% 记录后继续 |
| C 类匹配率 | 35–60% | < 10% 排查对齐问题 |
| 解码失败率 | < 1% | > 5% 立即停止（说明方法用错） |

---

## 6. 错误签名 → 处理

| 报错 / 现象 | 含义 | 处理 |
|---|---|---|
| `ssh_askpass: posix_spawnp` | Windows 找不到 askpass | askpass 放纯 ASCII 路径，设 `SSH_ASKPASS_REQUIRE=force` |
| `scp: subsystem request failed` | 没有 sftp | 改用 `ssh "cat > f"` 或 tar 流 |
| `below chunks` / `beyond chunks` | 逻辑地址超出 chunk 映射 | 跳过该候选，不要整批中断 |
| `short pread` | 源盘坏块 | 该段补零并计数，继续 |
| 进程 CPU 长时间为 0 | 卡在坏道 | 换盘或跳过该区间，不要等 |
| 走树结果 owner ≠ 目标子卷 | 旧树块被复用 | 换下一个旧根 |
| `Permission denied`（写 /tmp） | 之前 root 建过同名文件 | 临时文件名加 PID |
| 统计数 > 目标数 | 日志含重试重复行 | 改从磁盘反查 |

**通用规则**：遇到不认识的错误 → 记录到 `errors.log` 并继续下一个文件；同一错误连续出现 20 次 → 停下报告。

---

## 7. 进度与日志规范

必须维护：

| 文件 | 内容 |
|---|---|
| `state.json` | 当前阶段、计数、时间戳（每阶段更新） |
| `progress.txt` | 人类可读状态（每 60 秒刷新） |
| `errors.log` | 每条错误一行：时间、阶段、文件、错误 |
| `fail_*.tsv` | 分阶段失败清单 |

禁止：把所有逐文件日志打印到对话里（会淹没上下文）。**只汇报汇总数字。**

---

## 8. 停止与上报条件

出现以下任一情况，**停止当前阶段并写入 `需要确认.txt`**，等待人工确认：

1. A 类成功率 < 60%
2. bookend 前 200 个全失败
3. 空闲空间镜像字节数对不上
4. 解码失败率 > 5%
5. 落地盘剩余低于阈值（C 盘 20 GB）
6. 需要执行任何可能写源盘的操作

---

## 9. 交接检查表（任务结束前逐条确认）

- [ ] `state.json` 记录了每个阶段的成功/失败数
- [ ] 失败清单是从磁盘反查生成的
- [ ] 每个恢复文件都做过解码校验
- [ ] 统计表能和磁盘文件数对上
- [ ] 源盘没有任何写入（`find <SHARE> -newermt '-24 hours'` 应为空）
- [ ] 交付：恢复目录 + 失败清单 + 统计表 + 本 runbook 的执行记录

---

## 10. 参数速查

| 常量 | 值 |
|---|---|
| footer 长度 | 588 字节 |
| mode 偏移 | 572 |
| pct 偏移 | 573 |
| crypto 偏移 | 574（0x20 真 / 0x21 诱饵） |
| N 偏移 | 580，u64 小端 |
| 0x25 段长 | `ln = (N // 100) * PF[pct]`，`gap = (N - 3*ln) // 2` |
| PF 表 | 10:4 15:5 20:7 25:9 30:10 35:12 40:14 50:10 60:20 70:23 80:27 |
| A 类上限 | 128 MiB |
| O_NOATIME | 0o40000 |
