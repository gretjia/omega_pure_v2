## WHY Chain

1. C-028 仅以 doc_only 方式记录在 OMEGA_LESSONS.md
2. 推理 job 配置由 gen_inference_config.sh 模板生成
3. 模板在 C-028 之前编写，硬编码 bootDiskType=pd-ssd + bootDiskSizeGb=200
4. 编写新推理配置时，Claude 未查 OMEGA_LESSONS.md 中的 C-028 教训
5. 模板生成的每份配置都自带 pd-ssd + 200GB — 批量复制错误

## 为什么现有教训没拦住

C-028 记录了正确的教训（pd-ssd 吞吐与容量挂钩），但执法方式是 **doc_only**:
- OMEGA_LESSONS.md 是被动文档，需要人/AI 主动查阅
- gen_config 模板是主动执行的脚本，每次自动输出旧配置
- 教训存在于文档层，但错误根源在模板层
- "可记忆" (doc_only) 败给了 "可执行" (hardcoded template)

这正是 Ω4（可执行 > 可记忆）的反面教材: 文档级教训无法对抗模板级错误。

## 模式泛化

**配置模板是教训的反向传播路径**。当一个教训禁止某个配置值时，必须同时:
1. 记录到 OMEGA_LESSONS.md（人类可读）
2. 更新所有生成该配置值的模板/脚本（机器可执行）
3. 部署 hook 拦截该值的写入（防御兜底）

只做 (1) 而不做 (2)(3) = 教训必然被模板覆盖。这是 "经验衰减" 模式: 教训的半衰期取决于执法强度，doc_only 的半衰期约为 2-3 次操作。
