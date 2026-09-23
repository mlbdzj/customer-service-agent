from app.agent import agent
from app.memory import store
from app.handoff import should_handoff, judge_resolved

SESSION_ID = "cli-test"


def print_trace(messages):
    """打印 Agent 的工具调用过程"""
    for m in messages:
        if hasattr(m, "tool_calls") and m.tool_calls:
            for tc in m.tool_calls:
                print(f"   🔧 调用工具: {tc['name']}({tc['args']})")
        if getattr(m, "type", None) == "tool":
            print(f"   📦 工具返回: {m.content[:80]}...")


def handle_turn(user_input: str):
    state = store.get(SESSION_ID)          # ← 返回 SessionState，不再是 list

    # 已转人工，后续消息不再走 Agent
    if state.handoff_requested:
        print(f"\n🤖 客服: 您正在与人工客服对话中（原因：{state.handoff_reason}）")
        return

    # ★ 关键修复：用 state.messages 取历史消息
    messages = state.messages + [{"role": "user", "content": user_input}]
    result = agent.invoke({"messages": messages})
    reply = result["messages"][-1].content

    print("\n--- Agent 思考过程 ---")
    print_trace(result["messages"])

    # 更新消息历史
    store.append_messages(SESSION_ID, result["messages"])

    # 用独立模型判定本轮是否解决
    resolved = judge_resolved(user_input, reply)
    if resolved:
        store.mark_resolved(SESSION_ID)
    else:
        store.mark_unresolved(SESSION_ID)

    # 综合判定是否转人工
    current = store.get(SESSION_ID)
    need_handoff, reason = should_handoff(
        user_message=user_input,
        agent_reply=reply,
        unresolved_count=current.unresolved_count,
    )

    if need_handoff:
        store.set_handoff(SESSION_ID, reason)
        reply = f"{reply}\n\n[已为您转接人工客服，原因：{reason}]"

    print(f"\n🤖 客服: {reply}")
    print(f"   (未解决计数={current.unresolved_count}, 本轮解决={resolved}, 转人工={need_handoff})")


def main():
    print("电商客服 Agent 已启动")
    print("命令：exit 退出 | /debug 查看会话状态 | /clear 清空会话")
    print("=" * 50)

    while True:
        user_input = input("\n👤 用户: ").strip()
        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "退出"):
            print("再见！")
            break

        if user_input == "/debug":
            s = store.get(SESSION_ID)
            print(f"   未解决计数={s.unresolved_count} | 已转人工={s.handoff_requested} | "
                  f"原因={s.handoff_reason} | 消息数={len(s.messages)}")
            continue

        if user_input == "/clear":
            store.clear(SESSION_ID)
            print("   会话已清空")
            continue

        handle_turn(user_input)


if __name__ == "__main__":
    main()