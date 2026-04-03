## 修复

1. **gen_inference_config.sh 模板修复**:
   - bootDiskSizeGb: 200 → 1300 (容纳 556GB shards + OS + 缓冲)
   - 注释中标注 C-028 引用

2. **lesson-enforcer.sh hook 部署** (d3f5352):
   ```bash
   # PreToolUse hook — 拦截 pd-ssd 写入 YAML
   if grep -q "pd-ssd" "$file" && [[ "$file" == *.yaml ]]; then
       echo "BLOCKED: pd-ssd detected in $file (C-028 violation)"
       echo "Training must use Local SSD or FUSE v2 file-cache"
       # 交互确认，训练 job 默认拒绝
   fi
   ```

3. safe_submit.sh 中增加 C-028 检查（89b4ebf）:
   - 提交前扫描 YAML 中的 diskType
   - pd-ssd 配置需要交互确认

## 验证

- lesson-enforcer.sh 在后续 Phase 11 配置编写中成功拦截 pd-ssd 写入
- gen_inference_config.sh 生成的配置默认 1300GB
- safe_submit.sh 提交前检查通过

## 执法

executable — 三层防御:
1. `.claude/hooks/lesson-enforcer.sh` PreToolUse hook (自动拦截 pd-ssd 写入)
2. `gcp/gen_inference_config.sh` 模板固化 1300GB (消除模板级错误源)
3. `gcp/safe_submit.sh` 提交前 YAML 检查 (最后一道关卡)
