#!/usr/bin/env python3
"""
数据清理脚本
功能：删除 scripts.json 中超过 3 天的记录
用法: python3 cleanup_old_data.py
"""

import json, os, time
from datetime import datetime, timedelta

SCRIPTS_FILE = os.path.expanduser('~/.openclaw/workspace/doubao/sheet/scripts/data/scripts.json')
MAX_AGE_DAYS = 3

def main():
    print('🧹 数据清理脚本')
    print(f'   数据文件: {SCRIPTS_FILE}')
    print(f'   保留期限: {MAX_AGE_DAYS} 天')

    if not os.path.exists(SCRIPTS_FILE):
        print('⚠️ 数据文件不存在，无需清理')
        return

    # 读取数据
    try:
        with open(SCRIPTS_FILE, 'r', encoding='utf-8') as f:
            scripts = json.load(f)
    except json.JSONDecodeError as e:
        print(f'⚠️ JSON 解析失败: {e}')
        return
    except Exception as e:
        print(f'⚠️ 读取失败: {e}')
        return

    print(f'   当前记录数: {len(scripts)}')

    # 计算截止日期
    cutoff_date = datetime.now() - timedelta(days=MAX_AGE_DAYS)
    cutoff_str = cutoff_date.strftime('%Y-%m-%d')
    print(f'   截止日期: {cutoff_str} 之前的将被删除')

    # 过滤记录
    original_count = len(scripts)
    filtered_scripts = []
    removed_count = 0

    for script in scripts:
        date_str = script.get('date', '')
        if not date_str:
            # 没有日期的记录默认保留
            filtered_scripts.append(script)
            continue
        
        try:
            record_date = datetime.strptime(date_str, '%Y-%m-%d')
            if record_date >= cutoff_date:
                filtered_scripts.append(script)
            else:
                removed_count += 1
                print(f'   🗑️ 删除: ID={script.get("id")} 日期={date_str} 标题={script.get("title","")[:30]}')
        except ValueError:
            # 日期格式不对，保留
            filtered_scripts.append(script)

    # 保存
    if removed_count > 0:
        with open(SCRIPTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(filtered_scripts, f, ensure_ascii=False, indent=2)
        print(f'   ✅ 清理完成: 删除 {removed_count} 条，保留 {len(filtered_scripts)} 条')
    else:
        print('   ✅ 无需清理，没有过期记录')

    print()
    print('=' * 40)
    print(f'📊 清理报告')
    print(f'   原始记录: {original_count}')
    print(f'   删除记录: {removed_count}')
    print(f'   保留记录: {len(filtered_scripts)}')
    print('=' * 40)

if __name__ == '__main__':
    main()
