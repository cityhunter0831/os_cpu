from collections import deque
from typing import Optional, Deque, Dict, Set, List
from .process import Process, ProcessState


class Semaphore:
    def __init__(self, name: str, initial: int = 0):
        self.name = name
        self.value = initial
        self.wait_queue: Deque[Process] = deque()

    def wait(self, proc: Process) -> bool:
        """Return True if acquired, False if blocked (queued)."""
        if self.value > 0:
            self.value -= 1
            return True
        self.wait_queue.append(proc)
        return False

    def signal(self) -> Optional[Process]:
        """Signal semaphore. If any waiter, return unblocked process, else increment value."""
        if self.wait_queue:
            return self.wait_queue.popleft()
        self.value += 1
        return None


class Mutex:
    def __init__(self, name: str):
        self.name = name
        self.owner: Optional[Process] = None
        self.wait_queue: Deque[Process] = deque()

    def try_lock(self, proc: Process) -> bool:
        if self.owner is None:
            self.owner = proc
            return True
        if self.owner.pid == proc.pid:
            return True
        self.wait_queue.append(proc)
        return False

    def unlock(self) -> Optional[Process]:
        if self.wait_queue:
            next_p = self.wait_queue.popleft()
            self.owner = next_p
            return next_p
        self.owner = None
        return None


class SyncManager:
    """Holds all sync primitives and provides deadlock detection (WFG)."""

    def __init__(self):
        self.semaphores: Dict[str, Semaphore] = {}
        self.mutexes: Dict[str, Mutex] = {}

    def get_semaphore(self, name: str, initial: int = 0) -> Semaphore:
        if name not in self.semaphores:
            self.semaphores[name] = Semaphore(name, initial)
        return self.semaphores[name]

    def get_mutex(self, name: str) -> Mutex:
        if name not in self.mutexes:
            self.mutexes[name] = Mutex(name)
        return self.mutexes[name]

    def detect_deadlock(self) -> List[int]:
        """
        Build a simple Wait-For Graph (WFG) among processes for mutex ownership waits.
        Returns list of PIDs in a cycle if any, else empty.
        """
        # Build graph: edge A->B if A waits for mutex held by B
        graph: Dict[int, Set[int]] = {}
        nodes: Set[int] = set()
        for m in self.mutexes.values():
            holder = m.owner.pid if m.owner else None
            for w in m.wait_queue:
                nodes.add(w.pid)
                if holder is not None and holder != w.pid:
                    nodes.add(holder)
                    graph.setdefault(w.pid, set()).add(holder)
        # Cycle detection via DFS
        visited: Set[int] = set()
        stack: Set[int] = set()
        path: List[int] = []

        def dfs(u: int) -> Optional[List[int]]:
            visited.add(u)
            stack.add(u)
            path.append(u)
            for v in graph.get(u, ()): 
                if v not in visited:
                    cyc = dfs(v)
                    if cyc:
                        return cyc
                elif v in stack:
                    # cycle found; extract cycle segment
                    if v in path:
                        idx = path.index(v)
                        return path[idx:]
                    return [v]
            stack.remove(u)
            path.pop()
            return None

        for n in nodes:
            if n not in visited:
                cyc = dfs(n)
                if cyc:
                    return cyc
        return []
