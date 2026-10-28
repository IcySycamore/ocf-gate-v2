"""
    状态机
    包含事实类，状态类，批准类，转移规则
    应当实现状态持久化
    状态转移记录
    批准数量与预批准
"""
from enum import StrEnum, auto

class State(StrEnum):
    """
    状态机可用的状态枚举
    """
    READY=auto()
    ASKING=auto()
    PLANNING=auto()
    EXECUTING=auto()
    REPORTING=auto()
    BLOCKED=auto()

class Opinion(StrEnum):
    """
    人类批准态枚举
    """
    NONE=auto()
    APPROVE=auto()

class BaseFact:
    """
    机器事实类，用于存储状态机中的事实信息
    """
    def __init__(self, state: State, opinion: Opinion, pre_approval_counter:int, last_reason:str,error_counter:int):
        self.state = state
        self.opinion = opinion
        self.pre_approval_counter = pre_approval_counter
        self.last_reason = last_reason
        self.error_counter = error_counter

# 所有状态
ALL: frozenset[Opinion] = frozenset({Opinion.APPROVE,  Opinion.NONE})

# 允许执行的状态转换
transitions=[
            (State.READY,          ALL,                  State.ASKING),           # 自动进入受理态                                            by hook
            (State.ASKING,         ALL,                  State.READY),            # human只是询问时                                           by agent
            (State.ASKING,         ALL,                  State.PLANNING),         # agent受理拷问结束转入计划态                                by agent
            (State.ASKING,         ALL,                  State.BLOCKED),          # agent发现系统漏洞或失效                                    by agent
            (State.PLANNING,       ALL,                  State.ASKING),           # human拒绝并给出原因，agent继续拷问 或human有新的问题时       by human
            (State.PLANNING,       {Opinion.APPROVE},    State.EXECUTING),        # human批准并给出原因，agent继续执行                          by human
            (State.PLANNING,       ALL,                  State.BLOCKED),          # agent发现计划重大错误/受理共识不清晰 阻塞并给出原因           by agent
            (State.EXECUTING,      ALL,                  State.REPORTING),        # agent执行结束，给出报告                                     by agent
            (State.EXECUTING,      ALL,                  State.BLOCKED),          # agent发现错误，进入阻塞 或 命令错误计数达到上限               by agent or hook
            (State.REPORTING,      ALL,                  State.READY),            # agent报告结束，恢复就绪                                     by agent
            (State.BLOCKED,        ALL,                  State.READY)             # 阻塞因已清除，阻塞态解除，转入就绪态                          by human


]

def transition_attempt(fact: BaseFact, target_state: State) -> bool:

    """
        尝试执行状态转换.
        成功时会改变状态并返回Ture, 失败仅返回False.
    """
    # 当转换需要批准的转换时进行消耗预批准量
    if(fact.state==State.PLANNING and target_state==State.EXECUTING):
        return consume_approval(fact)

    # 当前允许的转换目标
    expected_state = [dst for src,ops,dst in transitions if(src==fact.state and (fact.opinion in ops))]

    # 无可用转换
    if not expected_state:
        return False

    # 转换不被允许
    if target_state not in expected_state:
        return False

    # 允许的转换,直接改变状态回报成功
    fact.state=target_state
    return True

def consume_approval(fact: BaseFact)->bool:
    """
        消耗批准数量
        先改变批准数量, 再改变批准状态.
    """
    if(fact.pre_approval_counter>=1):
        fact.pre_approval_counter-=1
        if(fact.pre_approval_counter==0):
            fact.opinion=Opinion.NONE
        return True
    return False

def on_approval(fact: BaseFact):
    """
        增加批准数量
        先改变批准状态，再改变批准数量
    """
    if(fact.pre_approval_counter==0):
        fact.opinion=Opinion.APPROVE
    fact.pre_approval_counter+=1

def pre_approval(fact: BaseFact,pre_approval:int):
    """
        预批准之后的 pre_approval_counter 次批准请求
    """
    for _ in range(pre_approval):
        on_approval(fact)

