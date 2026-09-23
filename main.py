from app.agent import agent
from app.memory import memory

SESSION_ID = "cli-test"


def print_trace(messages):
    """打印 Agent 的工具调用过程，方便观察 ReAct 循环"""
    for m in messages:
        if hasattr(m, "tool_calls") and m.tool_calls:
            for tc in m.tool_calls:
                print(f"   🔧 调用工具: {tc['name']}({tc['args']})")
        if getattr(m, "type", None) == "tool":
            print(f"   📦 工具返回: {m.content[:80]}...")


def main():
    print("电商客服 Agent 已启动（输入 exit 退出）\n" + "=" * 50)

    while True:
        user_input = input("\n👤 用户: ").strip()
        if user_input.lower() in ("exit", "quit", "退出"):
            print("再见！")
            break
        if not user_input:
            continue

        history = memory.get(SESSION_ID)
        messages = history + [{"role": "user", "content": user_input}]
        result = agent.invoke({"messages": messages})

        print("\n--- Agent 思考过程 ---")
        print_trace(result["messages"])

        memory.append(SESSION_ID, result["messages"])
        print(f"\n🤖 客服: {result['messages'][-1].content}")


if __name__ == "__main__":
    main()