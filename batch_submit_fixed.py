import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Any, Optional

def batch_submit(orders: list, http_post: Callable) -> dict:
    """将订单按类别分组，多线程并行提交，每批最多 5 个"""
    if not orders:
        return {"success": 0, "failed": 0}

    by_group = defaultdict(list)
    for order in orders:
        by_group[order['group']].append(order)

    lock = threading.Lock()
    total_ok = 0
    total_fail = 0
    hit_limit = threading.Event()

    def submit_group(group_orders: list) -> tuple:
        group_ok = 0
        group_fail = 0

        for i in range(0, len(group_orders), 5):
            if hit_limit.is_set():
                break

            chunk = group_orders[i:i + 5]
            res = None

            for retry in range(3):
                try:
                    res = http_post("/api/batch", {"items": chunk})
                except Exception:
                    if retry == 2:
                        group_fail += len(chunk)
                        break
                    time.sleep(1.5)
                    continue

                if res is None:
                    group_fail += len(chunk)
                    break

                if res.get("code") == 429:
                    time.sleep(1.5)
                    continue
                break

            if res is None or res.get("code") != 0:
                if res and res.get("code") == 40010:
                    hit_limit.set()
                group_fail += len(chunk)
                continue

            for item_result in res.get("results", []):
                if item_result.get("code") != 0:
                    group_fail += 1
                else:
                    group_ok += 1

        return group_ok, group_fail

    with ThreadPoolExecutor(max_workers=len(by_group)) as executor:
        futures = {
            executor.submit(submit_group, orders): group
            for group, orders in by_group.items()
        }

        for future in as_completed(futures):
            try:
                ok, fail = future.result()
                with lock:
                    total_ok += ok
                    total_fail += fail
            except Exception as e:
                print(f"组执行异常: {e}")

    return {"success": total_ok, "failed": total_fail}


if __name__ == "__main__":
    # 模拟测试
    def mock_http_post(url: str, data: dict) -> dict:
        return {"code": 0, "results": [{"code": 0}] * len(data["items"])}

    test_orders = [
        {"group": "A", "id": 1},
        {"group": "A", "id": 2},
        {"group": "B", "id": 3},
        {"group": "B", "id": 4},
        {"group": "B", "id": 5},
    ]

    result = batch_submit(test_orders, mock_http_post)
    print(f"Result: {result}")
    assert result == {"success": 5, "failed": 0}, f"测试失败: {result}"

    # 测试空输入
    assert batch_submit([], mock_http_post) == {"success": 0, "failed": 0}

    print("✅ 所有测试通过!")