import type { CodingContent } from '../guideTypes';

// ─────────────────────────────────────────────────────────────────────────────
// Long literals declared FIRST to avoid temporal dead zone when referenced
// inside the codingContent export below.
// Tasks 2.2 and 2.3 will fill in the remaining shelves and patterns.
// ─────────────────────────────────────────────────────────────────────────────

const CHEATSHEET_PATTERN_MATRIX_PARTIAL: CodingContent['cheatsheet']['patternMatrix'] = [
  // Task 2.3 will append 11 more entries to bring this to 14.
  {
    id: 'matrix-sliding-window',
    family: 'linear',
    trigger: 'longest or shortest contiguous range with a condition',
    state: 'window holds the largest valid range ending at r',
    move: 'expand r, update state, while invalid shrink l, record after valid',
    watch: 'with negative numbers, sum-based windows fail — use prefix sums',
  },
  {
    id: 'matrix-two-pointers',
    family: 'linear',
    trigger: 'sorted input with pair/triplet/partition pressure',
    state: 'left and right pointers preserve a sorted-order invariant',
    move: 'move the pointer that can improve the sorted condition',
    watch: 'duplicates after sort require a skip step',
  },
  {
    id: 'matrix-hash-map',
    family: 'linear',
    trigger: 'repeated lookup, counts, complements, first-unique',
    state: 'map = needed → first index, or value → count',
    move: 'check before insert when matching pairs by index',
    watch: 'inserting before checking allows self-pair when distinct indices required',
  },
  {
    id: 'matrix-sliding-fixed',
    family: 'linear',
    trigger: 'exactly-k window, fixed-size subarray max/min/sum',
    state: 'window [r-k+1, r] has constant size k; running sum stays updated',
    move: 'add numbers[r], subtract numbers[r-k], record after r >= k-1',
    watch: 'return early when input length is less than window size',
  },
  {
    id: 'matrix-prefix-sum',
    family: 'linear',
    trigger: 'range totals, subarray equals k, immutable repeated queries',
    state: 'prefix[i] = sum of numbers[0..i-1]; range sum = prefix[r+1] - prefix[l]',
    move: 'running += nums[i]; answer += count[running - target]; count[running]++',
    watch: 'with negatives, sum-based sliding window fails — use prefix sum + map instead',
  },
  {
    id: 'matrix-monostack',
    family: 'stack-heap',
    trigger: 'next greater/smaller element, histogram area, temperatures, span',
    state: 'stack holds pending indices in monotonic order waiting to be resolved',
    move: 'while stack top is dominated by current, pop and resolve top using current as boundary',
    watch: 'decide decreasing vs increasing stack direction before coding',
  },
  {
    id: 'matrix-bfs',
    family: 'graph',
    trigger: 'shortest unweighted path, nearest cell, level spread, minimum steps',
    state: 'visited set + queue; first pop of a node = shortest distance in unweighted graph',
    move: 'enqueue unvisited neighbors immediately when discovered, not when dequeued',
    watch: 'mark visited on enqueue, not dequeue — delays cause duplicates in the queue',
  },
  {
    id: 'matrix-dfs',
    family: 'graph',
    trigger: 'connected components, all paths, subtree aggregation, cycle detection',
    state: 'visited set tracks explored nodes; recursion stack represents the current path',
    move: 'visit, mark, recurse into unvisited neighbors, return aggregated result',
    watch: 'for directed cycle detection use white/gray/black coloring, not a simple visited set',
  },
  {
    id: 'matrix-topo-sort',
    family: 'graph',
    trigger: 'build order, course prerequisites, dependency resolution',
    state: 'indegreeByNode map; zero-indegree queue holds nodes safe to process next',
    move: 'pop zero-indegree node, decrement neighbors, enqueue any newly zeroed neighbors',
    watch: 'if processed count < total nodes, a cycle exists — return empty or signal invalid',
  },
  {
    id: 'matrix-union-find',
    family: 'graph',
    trigger: 'dynamic connectivity, number of islands, redundant connections',
    state: 'parentByItem and sizeByRoot; find() path-compresses; union merges smaller into larger',
    move: 'for each edge call union(a, b); return false if already connected (redundant edge)',
    watch: 'without path compression and union by rank, find() degrades to O(n) per call',
  },
  {
    id: 'matrix-heap-top-k',
    family: 'stack-heap',
    trigger: 'top k largest/smallest, k-th element, merge k sorted streams',
    state: 'min-heap of size k; heap top is the smallest of the k best seen so far',
    move: 'push each item; if heap size exceeds k, pop the min; final heap holds top k',
    watch: 'heap comparator direction determines largest-k vs smallest-k — verify before coding',
  },
  {
    id: 'matrix-heap-two-heaps',
    family: 'stack-heap',
    trigger: 'running median, sliding median, balanced partition',
    state: 'maxHeap holds lower half, minHeap holds upper half; sizes differ by at most 1',
    move: 'push to maxHeap, rebalance if tops are out of order, balance sizes by transferring top',
    watch: 'after every insert re-check both the order invariant and the size-balance invariant',
  },
  {
    id: 'matrix-backtracking',
    family: 'backtracking',
    trigger: 'all subsets/permutations/combinations, constraint-satisfaction, maze paths',
    state: 'currentPath holds the partial choice; startIndex or usedFlags tracks available items',
    move: 'choose item, add to path, recurse, then undo (remove from path)',
    watch: 'duplicates: sort first, then skip nums[i] when i > startIndex and nums[i] == nums[i-1]',
  },
  {
    id: 'matrix-1d-dp',
    family: 'dp',
    trigger: 'count/min/max over choices on a 1D sequence, coin change, climb stairs, LIS',
    state: 'dp[i] = best answer for prefix ending at index i',
    move: 'dp[i] = f(dp[i-1], dp[i-2], ...) based on last choice; fill left to right',
    watch: 'set all base cases before the loop; missing one causes silently wrong answers',
  },
];

const ARRAY_TOOLKIT_IMPL: Record<'python' | 'javascript' | 'java', string> = {
  python: `class ArrayToolkit:
    @staticmethod
    def binary_search(sorted_numbers, target):
        left_index, right_index = 0, len(sorted_numbers) - 1
        while left_index <= right_index:
            middle_index = left_index + (right_index - left_index) // 2
            middle_value = sorted_numbers[middle_index]
            if middle_value == target:
                return middle_index
            if middle_value < target:
                left_index = middle_index + 1
            else:
                right_index = middle_index - 1
        return -1

    @staticmethod
    def find_pair_with_target(numbers, target_sum):
        index_by_needed_value = {}
        for current_index, current_number in enumerate(numbers):
            if current_number in index_by_needed_value:
                return (index_by_needed_value[current_number], current_index)
            index_by_needed_value[target_sum - current_number] = current_index
        return None

    @staticmethod
    def longest_subarray_with_sum_at_most(numbers, sum_limit):
        left_index = 0
        running_sum = 0
        best_length = 0
        for right_index, added_number in enumerate(numbers):
            running_sum += added_number
            while running_sum > sum_limit and left_index <= right_index:
                running_sum -= numbers[left_index]
                left_index += 1
            best_length = max(best_length, right_index - left_index + 1)
        return best_length

    @staticmethod
    def rotate_in_place(values, shift_amount):
        size = len(values)
        normalized_shift = shift_amount % size if size else 0
        ArrayToolkit._reverse(values, 0, size - 1)
        ArrayToolkit._reverse(values, 0, normalized_shift - 1)
        ArrayToolkit._reverse(values, normalized_shift, size - 1)

    @staticmethod
    def _reverse(values, left_index, right_index):
        while left_index < right_index:
            values[left_index], values[right_index] = values[right_index], values[left_index]
            left_index += 1
            right_index -= 1

    @staticmethod
    def sliding_window_max(numbers, window_size):
        from collections import deque
        candidate_indices = deque()
        window_max_values = []
        for right_index, current_number in enumerate(numbers):
            while candidate_indices and candidate_indices[0] <= right_index - window_size:
                candidate_indices.popleft()
            while candidate_indices and numbers[candidate_indices[-1]] < current_number:
                candidate_indices.pop()
            candidate_indices.append(right_index)
            if right_index >= window_size - 1:
                window_max_values.append(numbers[candidate_indices[0]])
        return window_max_values

    @staticmethod
    def partition_around_pivot(values, left_index, right_index):
        pivot_value = values[right_index]
        store_index = left_index
        for scan_index in range(left_index, right_index):
            if values[scan_index] < pivot_value:
                values[store_index], values[scan_index] = values[scan_index], values[store_index]
                store_index += 1
        values[store_index], values[right_index] = values[right_index], values[store_index]
        return store_index`,
  javascript: `class ArrayToolkit {
  static binarySearch(sortedNumbers, target) {
    let leftIndex = 0;
    let rightIndex = sortedNumbers.length - 1;
    while (leftIndex <= rightIndex) {
      const middleIndex = leftIndex + Math.floor((rightIndex - leftIndex) / 2);
      const middleValue = sortedNumbers[middleIndex];
      if (middleValue === target) return middleIndex;
      if (middleValue < target) leftIndex = middleIndex + 1;
      else rightIndex = middleIndex - 1;
    }
    return -1;
  }

  static findPairWithTarget(numbers, targetSum) {
    const indexByNeededValue = new Map();
    for (let currentIndex = 0; currentIndex < numbers.length; currentIndex += 1) {
      const currentNumber = numbers[currentIndex];
      if (indexByNeededValue.has(currentNumber)) {
        return [indexByNeededValue.get(currentNumber), currentIndex];
      }
      indexByNeededValue.set(targetSum - currentNumber, currentIndex);
    }
    return null;
  }

  static longestSubarrayWithSumAtMost(numbers, sumLimit) {
    let leftIndex = 0;
    let runningSum = 0;
    let bestLength = 0;
    for (let rightIndex = 0; rightIndex < numbers.length; rightIndex += 1) {
      runningSum += numbers[rightIndex];
      while (runningSum > sumLimit && leftIndex <= rightIndex) {
        runningSum -= numbers[leftIndex];
        leftIndex += 1;
      }
      bestLength = Math.max(bestLength, rightIndex - leftIndex + 1);
    }
    return bestLength;
  }

  static rotateInPlace(values, shiftAmount) {
    const size = values.length;
    const normalizedShift = size ? shiftAmount % size : 0;
    ArrayToolkit._reverse(values, 0, size - 1);
    ArrayToolkit._reverse(values, 0, normalizedShift - 1);
    ArrayToolkit._reverse(values, normalizedShift, size - 1);
  }

  static _reverse(values, leftIndex, rightIndex) {
    while (leftIndex < rightIndex) {
      [values[leftIndex], values[rightIndex]] = [values[rightIndex], values[leftIndex]];
      leftIndex += 1;
      rightIndex -= 1;
    }
  }

  static slidingWindowMax(numbers, windowSize) {
    const candidateIndices = [];
    const windowMaxValues = [];
    for (let rightIndex = 0; rightIndex < numbers.length; rightIndex += 1) {
      const currentNumber = numbers[rightIndex];
      while (candidateIndices.length && candidateIndices[0] <= rightIndex - windowSize) {
        candidateIndices.shift();
      }
      while (candidateIndices.length && numbers[candidateIndices[candidateIndices.length - 1]] < currentNumber) {
        candidateIndices.pop();
      }
      candidateIndices.push(rightIndex);
      if (rightIndex >= windowSize - 1) {
        windowMaxValues.push(numbers[candidateIndices[0]]);
      }
    }
    return windowMaxValues;
  }
}`,
  java: `import java.util.*;

class ArrayToolkit {
    static int binarySearch(int[] sortedNumbers, int target) {
        int leftIndex = 0;
        int rightIndex = sortedNumbers.length - 1;
        while (leftIndex <= rightIndex) {
            int middleIndex = leftIndex + (rightIndex - leftIndex) / 2;
            int middleValue = sortedNumbers[middleIndex];
            if (middleValue == target) return middleIndex;
            if (middleValue < target) leftIndex = middleIndex + 1;
            else rightIndex = middleIndex - 1;
        }
        return -1;
    }

    static int[] findPairWithTarget(int[] numbers, int targetSum) {
        Map<Integer, Integer> indexByNeededValue = new HashMap<>();
        for (int currentIndex = 0; currentIndex < numbers.length; currentIndex++) {
            int currentNumber = numbers[currentIndex];
            if (indexByNeededValue.containsKey(currentNumber)) {
                return new int[] { indexByNeededValue.get(currentNumber), currentIndex };
            }
            indexByNeededValue.put(targetSum - currentNumber, currentIndex);
        }
        return new int[] {};
    }

    static int longestSubarrayWithSumAtMost(int[] numbers, int sumLimit) {
        int leftIndex = 0;
        int runningSum = 0;
        int bestLength = 0;
        for (int rightIndex = 0; rightIndex < numbers.length; rightIndex++) {
            runningSum += numbers[rightIndex];
            while (runningSum > sumLimit && leftIndex <= rightIndex) {
                runningSum -= numbers[leftIndex];
                leftIndex++;
            }
            bestLength = Math.max(bestLength, rightIndex - leftIndex + 1);
        }
        return bestLength;
    }
}`,
};

const SINGLY_LINKED_LIST_IMPL: Record<'python' | 'javascript' | 'java', string> = {
  python: `class ListNode:
    def __init__(self, value):
        self.value = value
        self.next = None

class SinglyLinkedList:
    def __init__(self):
        self.head = None
        self.tail = None

    def append(self, value):
        new_node = ListNode(value)
        if self.head is None:
            self.head = new_node
        else:
            self.tail.next = new_node
        self.tail = new_node
        return new_node

    def prepend(self, value):
        new_node = ListNode(value)
        new_node.next = self.head
        self.head = new_node
        if self.tail is None:
            self.tail = new_node
        return new_node

    def reverse(self):
        previous_node = None
        current_node = self.head
        self.tail = self.head
        while current_node is not None:
            next_node = current_node.next
            current_node.next = previous_node
            previous_node = current_node
            current_node = next_node
        self.head = previous_node

    def find_middle(self):
        slow_node = self.head
        fast_node = self.head
        while fast_node is not None and fast_node.next is not None:
            slow_node = slow_node.next
            fast_node = fast_node.next.next
        return slow_node

    def has_cycle(self):
        slow_node = self.head
        fast_node = self.head
        while fast_node is not None and fast_node.next is not None:
            slow_node = slow_node.next
            fast_node = fast_node.next.next
            if slow_node is fast_node:
                return True
        return False

    def find_cycle_start(self):
        slow_node = self.head
        fast_node = self.head
        while fast_node is not None and fast_node.next is not None:
            slow_node = slow_node.next
            fast_node = fast_node.next.next
            if slow_node is fast_node:
                entry_node = self.head
                while entry_node is not slow_node:
                    entry_node = entry_node.next
                    slow_node = slow_node.next
                return entry_node
        return None

    def remove_nth_from_end(self, n):
        dummy_node = ListNode(0)
        dummy_node.next = self.head
        leading_node = dummy_node
        trailing_node = dummy_node
        for _ in range(n + 1):
            leading_node = leading_node.next
        while leading_node is not None:
            leading_node = leading_node.next
            trailing_node = trailing_node.next
        trailing_node.next = trailing_node.next.next
        self.head = dummy_node.next

    def merge_sorted(self, other_list):
        dummy_node = ListNode(0)
        current_node = dummy_node
        left_node = self.head
        right_node = other_list.head
        while left_node is not None and right_node is not None:
            if left_node.value <= right_node.value:
                current_node.next = left_node
                left_node = left_node.next
            else:
                current_node.next = right_node
                right_node = right_node.next
            current_node = current_node.next
        current_node.next = left_node if left_node is not None else right_node
        while current_node.next is not None:
            current_node = current_node.next
        self.head = dummy_node.next
        self.tail = current_node

    def intersection_node(self, other_list):
        pointer_a = self.head
        pointer_b = other_list.head
        while pointer_a is not pointer_b:
            pointer_a = pointer_a.next if pointer_a is not None else other_list.head
            pointer_b = pointer_b.next if pointer_b is not None else self.head
        return pointer_a`,
  javascript: `class ListNode {
  constructor(value) {
    this.value = value;
    this.next = null;
  }
}

class SinglyLinkedList {
  constructor() {
    this.head = null;
    this.tail = null;
  }

  append(value) {
    const newNode = new ListNode(value);
    if (!this.head) this.head = newNode;
    else this.tail.next = newNode;
    this.tail = newNode;
    return newNode;
  }

  prepend(value) {
    const newNode = new ListNode(value);
    newNode.next = this.head;
    this.head = newNode;
    if (!this.tail) this.tail = newNode;
    return newNode;
  }

  reverse() {
    let previousNode = null;
    let currentNode = this.head;
    this.tail = this.head;
    while (currentNode) {
      const nextNode = currentNode.next;
      currentNode.next = previousNode;
      previousNode = currentNode;
      currentNode = nextNode;
    }
    this.head = previousNode;
  }

  findMiddle() {
    let slowNode = this.head;
    let fastNode = this.head;
    while (fastNode?.next) {
      slowNode = slowNode.next;
      fastNode = fastNode.next.next;
    }
    return slowNode;
  }

  hasCycle() {
    let slowNode = this.head;
    let fastNode = this.head;
    while (fastNode?.next) {
      slowNode = slowNode.next;
      fastNode = fastNode.next.next;
      if (slowNode === fastNode) return true;
    }
    return false;
  }

  findCycleStart() {
    let slowNode = this.head;
    let fastNode = this.head;
    while (fastNode?.next) {
      slowNode = slowNode.next;
      fastNode = fastNode.next.next;
      if (slowNode === fastNode) {
        let entryNode = this.head;
        while (entryNode !== slowNode) {
          entryNode = entryNode.next;
          slowNode = slowNode.next;
        }
        return entryNode;
      }
    }
    return null;
  }

  removeNthFromEnd(n) {
    const dummyNode = new ListNode(0);
    dummyNode.next = this.head;
    let leadingNode = dummyNode;
    let trailingNode = dummyNode;
    for (let step = 0; step <= n; step += 1) leadingNode = leadingNode.next;
    while (leadingNode !== null) {
      leadingNode = leadingNode.next;
      trailingNode = trailingNode.next;
    }
    trailingNode.next = trailingNode.next.next;
    this.head = dummyNode.next;
  }

  mergeSorted(otherList) {
    const dummyNode = new ListNode(0);
    let currentNode = dummyNode;
    let leftNode = this.head;
    let rightNode = otherList.head;
    while (leftNode && rightNode) {
      if (leftNode.value <= rightNode.value) {
        currentNode.next = leftNode;
        leftNode = leftNode.next;
      } else {
        currentNode.next = rightNode;
        rightNode = rightNode.next;
      }
      currentNode = currentNode.next;
    }
    currentNode.next = leftNode ?? rightNode;
    while (currentNode.next) currentNode = currentNode.next;
    this.head = dummyNode.next;
    this.tail = currentNode;
  }

  intersectionNode(otherList) {
    let pointerA = this.head;
    let pointerB = otherList.head;
    while (pointerA !== pointerB) {
      pointerA = pointerA !== null ? pointerA.next : otherList.head;
      pointerB = pointerB !== null ? pointerB.next : this.head;
    }
    return pointerA;
  }
}`,
  java: `class SinglyLinkedList<T> {
    static class ListNode<T> {
        T value;
        ListNode<T> next;
        ListNode(T value) { this.value = value; }
    }

    ListNode<T> head;
    ListNode<T> tail;

    void append(T value) {
        ListNode<T> newNode = new ListNode<>(value);
        if (head == null) head = newNode;
        else tail.next = newNode;
        tail = newNode;
    }

    void prepend(T value) {
        ListNode<T> newNode = new ListNode<>(value);
        newNode.next = head;
        head = newNode;
        if (tail == null) tail = newNode;
    }

    void reverse() {
        ListNode<T> previousNode = null;
        ListNode<T> currentNode = head;
        tail = head;
        while (currentNode != null) {
            ListNode<T> nextNode = currentNode.next;
            currentNode.next = previousNode;
            previousNode = currentNode;
            currentNode = nextNode;
        }
        head = previousNode;
    }

    ListNode<T> findMiddle() {
        ListNode<T> slowNode = head;
        ListNode<T> fastNode = head;
        while (fastNode != null && fastNode.next != null) {
            slowNode = slowNode.next;
            fastNode = fastNode.next.next;
        }
        return slowNode;
    }

    boolean hasCycle() {
        ListNode<T> slowNode = head;
        ListNode<T> fastNode = head;
        while (fastNode != null && fastNode.next != null) {
            slowNode = slowNode.next;
            fastNode = fastNode.next.next;
            if (slowNode == fastNode) return true;
        }
        return false;
    }

    ListNode<T> findCycleStart() {
        ListNode<T> slowNode = head;
        ListNode<T> fastNode = head;
        while (fastNode != null && fastNode.next != null) {
            slowNode = slowNode.next;
            fastNode = fastNode.next.next;
            if (slowNode == fastNode) {
                ListNode<T> entryNode = head;
                while (entryNode != slowNode) {
                    entryNode = entryNode.next;
                    slowNode = slowNode.next;
                }
                return entryNode;
            }
        }
        return null;
    }

    void removeNthFromEnd(int n) {
        ListNode<T> dummyNode = new ListNode<>(null);
        dummyNode.next = head;
        ListNode<T> leadingNode = dummyNode;
        ListNode<T> trailingNode = dummyNode;
        for (int step = 0; step <= n; step++) leadingNode = leadingNode.next;
        while (leadingNode != null) {
            leadingNode = leadingNode.next;
            trailingNode = trailingNode.next;
        }
        trailingNode.next = trailingNode.next.next;
        head = dummyNode.next;
    }

    void mergeSorted(SinglyLinkedList<T> otherList, java.util.Comparator<T> comparator) {
        ListNode<T> dummyNode = new ListNode<>(null);
        ListNode<T> currentNode = dummyNode;
        ListNode<T> leftNode = head;
        ListNode<T> rightNode = otherList.head;
        while (leftNode != null && rightNode != null) {
            if (comparator.compare(leftNode.value, rightNode.value) <= 0) {
                currentNode.next = leftNode;
                leftNode = leftNode.next;
            } else {
                currentNode.next = rightNode;
                rightNode = rightNode.next;
            }
            currentNode = currentNode.next;
        }
        currentNode.next = (leftNode != null) ? leftNode : rightNode;
        while (currentNode.next != null) currentNode = currentNode.next;
        head = dummyNode.next;
        tail = currentNode;
    }

    ListNode<T> intersectionNode(SinglyLinkedList<T> otherList) {
        ListNode<T> pointerA = head;
        ListNode<T> pointerB = otherList.head;
        while (pointerA != pointerB) {
            pointerA = (pointerA != null) ? pointerA.next : otherList.head;
            pointerB = (pointerB != null) ? pointerB.next : head;
        }
        return pointerA;
    }
}`,
};

const GRAPH_IMPL: Record<'python' | 'javascript' | 'java', string> = {
  python: `from collections import defaultdict, deque

class Graph:
    def __init__(self):
        self.neighbors_by_node = defaultdict(set)

    def add_undirected_edge(self, first_node, second_node):
        self.neighbors_by_node[first_node].add(second_node)
        self.neighbors_by_node[second_node].add(first_node)

    def add_directed_edge(self, source_node, target_node):
        self.neighbors_by_node[source_node].add(target_node)
        self.neighbors_by_node.setdefault(target_node, set())

    def bfs(self, start_node):
        visited_nodes = {start_node}
        queue = deque([start_node])
        traversal_order = []
        while queue:
            current_node = queue.popleft()
            traversal_order.append(current_node)
            for neighbor in self.neighbors_by_node[current_node]:
                if neighbor not in visited_nodes:
                    visited_nodes.add(neighbor)
                    queue.append(neighbor)
        return traversal_order

    def dfs(self, start_node):
        traversal_order = []
        visited_nodes = set()
        def visit(node):
            if node in visited_nodes:
                return
            visited_nodes.add(node)
            traversal_order.append(node)
            for neighbor in self.neighbors_by_node[node]:
                visit(neighbor)
        visit(start_node)
        return traversal_order

    def find_shortest_unweighted_path(self, start_node, target_node):
        visited_nodes = {start_node}
        queue = deque([(start_node, [start_node])])
        while queue:
            current_node, current_path = queue.popleft()
            if current_node == target_node:
                return current_path
            for neighbor in self.neighbors_by_node[current_node]:
                if neighbor not in visited_nodes:
                    visited_nodes.add(neighbor)
                    queue.append((neighbor, current_path + [neighbor]))
        return None

    def count_components(self):
        visited_nodes = set()
        component_count = 0
        for node in self.neighbors_by_node:
            if node not in visited_nodes:
                component_count += 1
                stack = [node]
                while stack:
                    current_node = stack.pop()
                    if current_node in visited_nodes:
                        continue
                    visited_nodes.add(current_node)
                    for neighbor in self.neighbors_by_node[current_node]:
                        if neighbor not in visited_nodes:
                            stack.append(neighbor)
        return component_count

    def has_cycle_directed(self):
        WHITE, GRAY, BLACK = 0, 1, 2
        color_by_node = defaultdict(int)
        def dfs_visit(node):
            color_by_node[node] = GRAY
            for neighbor in self.neighbors_by_node[node]:
                if color_by_node[neighbor] == GRAY:
                    return True
                if color_by_node[neighbor] == WHITE and dfs_visit(neighbor):
                    return True
            color_by_node[node] = BLACK
            return False
        for node in list(self.neighbors_by_node):
            if color_by_node[node] == WHITE and dfs_visit(node):
                return True
        return False

    def topological_order(self):
        indegree_by_node = defaultdict(int)
        for node in self.neighbors_by_node:
            indegree_by_node.setdefault(node, 0)
            for neighbor in self.neighbors_by_node[node]:
                indegree_by_node[neighbor] += 1
        zero_indegree_queue = deque(
            node for node, indegree in indegree_by_node.items() if indegree == 0
        )
        ordered_nodes = []
        while zero_indegree_queue:
            current_node = zero_indegree_queue.popleft()
            ordered_nodes.append(current_node)
            for neighbor in self.neighbors_by_node[current_node]:
                indegree_by_node[neighbor] -= 1
                if indegree_by_node[neighbor] == 0:
                    zero_indegree_queue.append(neighbor)
        return ordered_nodes if len(ordered_nodes) == len(indegree_by_node) else []`,
  javascript: `class Graph {
  constructor() {
    this.neighborsByNode = new Map();
  }

  _ensureNode(node) {
    if (!this.neighborsByNode.has(node)) this.neighborsByNode.set(node, new Set());
  }

  addUndirectedEdge(firstNode, secondNode) {
    this._ensureNode(firstNode);
    this._ensureNode(secondNode);
    this.neighborsByNode.get(firstNode).add(secondNode);
    this.neighborsByNode.get(secondNode).add(firstNode);
  }

  addDirectedEdge(sourceNode, targetNode) {
    this._ensureNode(sourceNode);
    this._ensureNode(targetNode);
    this.neighborsByNode.get(sourceNode).add(targetNode);
  }

  bfs(startNode) {
    const visitedNodes = new Set([startNode]);
    const queue = [startNode];
    const traversalOrder = [];
    for (let queueIndex = 0; queueIndex < queue.length; queueIndex += 1) {
      const currentNode = queue[queueIndex];
      traversalOrder.push(currentNode);
      for (const neighbor of this.neighborsByNode.get(currentNode) ?? []) {
        if (!visitedNodes.has(neighbor)) {
          visitedNodes.add(neighbor);
          queue.push(neighbor);
        }
      }
    }
    return traversalOrder;
  }

  dfs(startNode) {
    const traversalOrder = [];
    const visitedNodes = new Set();
    const visit = (node) => {
      if (visitedNodes.has(node)) return;
      visitedNodes.add(node);
      traversalOrder.push(node);
      for (const neighbor of this.neighborsByNode.get(node) ?? []) visit(neighbor);
    };
    visit(startNode);
    return traversalOrder;
  }

  findShortestUnweightedPath(startNode, targetNode) {
    const visitedNodes = new Set([startNode]);
    const queue = [{ node: startNode, path: [startNode] }];
    for (let queueIndex = 0; queueIndex < queue.length; queueIndex += 1) {
      const { node: currentNode, path: currentPath } = queue[queueIndex];
      if (currentNode === targetNode) return currentPath;
      for (const neighbor of this.neighborsByNode.get(currentNode) ?? []) {
        if (!visitedNodes.has(neighbor)) {
          visitedNodes.add(neighbor);
          queue.push({ node: neighbor, path: [...currentPath, neighbor] });
        }
      }
    }
    return null;
  }

  countComponents() {
    const visitedNodes = new Set();
    let componentCount = 0;
    for (const node of this.neighborsByNode.keys()) {
      if (visitedNodes.has(node)) continue;
      componentCount += 1;
      const stack = [node];
      while (stack.length > 0) {
        const currentNode = stack.pop();
        if (visitedNodes.has(currentNode)) continue;
        visitedNodes.add(currentNode);
        for (const neighbor of this.neighborsByNode.get(currentNode) ?? []) {
          if (!visitedNodes.has(neighbor)) stack.push(neighbor);
        }
      }
    }
    return componentCount;
  }

  hasCycleDirected() {
    const WHITE = 0, GRAY = 1, BLACK = 2;
    const colorByNode = new Map();
    const dfsVisit = (node) => {
      colorByNode.set(node, GRAY);
      for (const neighbor of this.neighborsByNode.get(node) ?? []) {
        if (colorByNode.get(neighbor) === GRAY) return true;
        if (!colorByNode.has(neighbor) && dfsVisit(neighbor)) return true;
      }
      colorByNode.set(node, BLACK);
      return false;
    };
    for (const node of this.neighborsByNode.keys()) {
      if (!colorByNode.has(node) && dfsVisit(node)) return true;
    }
    return false;
  }

  topologicalOrder() {
    const indegreeByNode = new Map();
    for (const node of this.neighborsByNode.keys()) {
      if (!indegreeByNode.has(node)) indegreeByNode.set(node, 0);
      for (const neighbor of this.neighborsByNode.get(node)) {
        indegreeByNode.set(neighbor, (indegreeByNode.get(neighbor) ?? 0) + 1);
      }
    }
    const zeroIndegreeQueue = [...indegreeByNode.entries()]
      .filter(([, indegree]) => indegree === 0)
      .map(([node]) => node);
    const orderedNodes = [];
    for (let queueIndex = 0; queueIndex < zeroIndegreeQueue.length; queueIndex += 1) {
      const currentNode = zeroIndegreeQueue[queueIndex];
      orderedNodes.push(currentNode);
      for (const neighbor of this.neighborsByNode.get(currentNode) ?? []) {
        const newIndegree = indegreeByNode.get(neighbor) - 1;
        indegreeByNode.set(neighbor, newIndegree);
        if (newIndegree === 0) zeroIndegreeQueue.push(neighbor);
      }
    }
    return orderedNodes.length === indegreeByNode.size ? orderedNodes : [];
  }
}`,
  java: `import java.util.*;

class Graph<T> {
    private final Map<T, Set<T>> neighborsByNode = new HashMap<>();

    private void ensureNode(T node) {
        neighborsByNode.computeIfAbsent(node, ignored -> new HashSet<>());
    }

    void addUndirectedEdge(T firstNode, T secondNode) {
        ensureNode(firstNode);
        ensureNode(secondNode);
        neighborsByNode.get(firstNode).add(secondNode);
        neighborsByNode.get(secondNode).add(firstNode);
    }

    void addDirectedEdge(T sourceNode, T targetNode) {
        ensureNode(sourceNode);
        ensureNode(targetNode);
        neighborsByNode.get(sourceNode).add(targetNode);
    }

    List<T> bfs(T startNode) {
        Set<T> visitedNodes = new HashSet<>();
        Queue<T> queue = new ArrayDeque<>();
        List<T> traversalOrder = new ArrayList<>();
        visitedNodes.add(startNode);
        queue.offer(startNode);
        while (!queue.isEmpty()) {
            T currentNode = queue.poll();
            traversalOrder.add(currentNode);
            for (T neighbor : neighborsByNode.getOrDefault(currentNode, Set.of())) {
                if (visitedNodes.add(neighbor)) queue.offer(neighbor);
            }
        }
        return traversalOrder;
    }

    List<T> dfs(T startNode) {
        List<T> traversalOrder = new ArrayList<>();
        Set<T> visitedNodes = new HashSet<>();
        dfsVisit(startNode, visitedNodes, traversalOrder);
        return traversalOrder;
    }

    private void dfsVisit(T node, Set<T> visitedNodes, List<T> traversalOrder) {
        if (!visitedNodes.add(node)) return;
        traversalOrder.add(node);
        for (T neighbor : neighborsByNode.getOrDefault(node, Set.of())) {
            dfsVisit(neighbor, visitedNodes, traversalOrder);
        }
    }

    List<T> findShortestUnweightedPath(T startNode, T targetNode) {
        Set<T> visitedNodes = new HashSet<>();
        Queue<List<T>> queue = new ArrayDeque<>();
        visitedNodes.add(startNode);
        queue.offer(new ArrayList<>(List.of(startNode)));
        while (!queue.isEmpty()) {
            List<T> currentPath = queue.poll();
            T currentNode = currentPath.get(currentPath.size() - 1);
            if (currentNode.equals(targetNode)) return currentPath;
            for (T neighbor : neighborsByNode.getOrDefault(currentNode, Set.of())) {
                if (visitedNodes.add(neighbor)) {
                    List<T> nextPath = new ArrayList<>(currentPath);
                    nextPath.add(neighbor);
                    queue.offer(nextPath);
                }
            }
        }
        return List.of();
    }

    int countComponents() {
        Set<T> visitedNodes = new HashSet<>();
        int componentCount = 0;
        for (T node : neighborsByNode.keySet()) {
            if (visitedNodes.contains(node)) continue;
            componentCount += 1;
            Deque<T> stack = new ArrayDeque<>();
            stack.push(node);
            while (!stack.isEmpty()) {
                T currentNode = stack.pop();
                if (!visitedNodes.add(currentNode)) continue;
                for (T neighbor : neighborsByNode.getOrDefault(currentNode, Set.of())) {
                    if (!visitedNodes.contains(neighbor)) stack.push(neighbor);
                }
            }
        }
        return componentCount;
    }

    boolean hasCycleDirected() {
        final int WHITE = 0, GRAY = 1, BLACK = 2;
        Map<T, Integer> colorByNode = new HashMap<>();
        for (T node : neighborsByNode.keySet()) {
            if (!colorByNode.containsKey(node) && dfsHasCycle(node, colorByNode, WHITE, GRAY, BLACK)) {
                return true;
            }
        }
        return false;
    }

    private boolean dfsHasCycle(T node, Map<T, Integer> colorByNode, int WHITE, int GRAY, int BLACK) {
        colorByNode.put(node, GRAY);
        for (T neighbor : neighborsByNode.getOrDefault(node, Set.of())) {
            int neighborColor = colorByNode.getOrDefault(neighbor, WHITE);
            if (neighborColor == GRAY) return true;
            if (neighborColor == WHITE && dfsHasCycle(neighbor, colorByNode, WHITE, GRAY, BLACK)) return true;
        }
        colorByNode.put(node, BLACK);
        return false;
    }

    List<T> topologicalOrder() {
        Map<T, Integer> indegreeByNode = new HashMap<>();
        for (T node : neighborsByNode.keySet()) {
            indegreeByNode.putIfAbsent(node, 0);
            for (T neighbor : neighborsByNode.get(node)) {
                indegreeByNode.merge(neighbor, 1, Integer::sum);
            }
        }
        Queue<T> zeroIndegreeQueue = new ArrayDeque<>();
        for (Map.Entry<T, Integer> entry : indegreeByNode.entrySet()) {
            if (entry.getValue() == 0) zeroIndegreeQueue.offer(entry.getKey());
        }
        List<T> orderedNodes = new ArrayList<>();
        while (!zeroIndegreeQueue.isEmpty()) {
            T currentNode = zeroIndegreeQueue.poll();
            orderedNodes.add(currentNode);
            for (T neighbor : neighborsByNode.getOrDefault(currentNode, Set.of())) {
                int newIndegree = indegreeByNode.merge(neighbor, -1, Integer::sum);
                if (newIndegree == 0) zeroIndegreeQueue.offer(neighbor);
            }
        }
        return orderedNodes.size() == indegreeByNode.size() ? orderedNodes : List.of();
    }
}`,
};

const FREQUENCY_COUNTER_SET_TOOLKIT_IMPL: Record<'python' | 'javascript' | 'java', string> = {
  python: `from collections import Counter, defaultdict

class FrequencyCounter:
    def __init__(self):
        self.count_by_item = defaultdict(int)

    def add(self, item):
        self.count_by_item[item] += 1

    def count(self, item):
        return self.count_by_item[item]

    def most_common(self, limit):
        return Counter(self.count_by_item).most_common(limit)

    def decrement(self, item):
        if self.count_by_item[item] > 0:
            self.count_by_item[item] -= 1
        if self.count_by_item[item] == 0:
            del self.count_by_item[item]

class SetToolkit:
    @staticmethod
    def has_duplicate(items):
        return len(set(items)) != len(items)

    @staticmethod
    def stable_intersection(first_items, second_items):
        second_set = set(second_items)
        return [item for item in dict.fromkeys(first_items) if item in second_set]

    @staticmethod
    def dedupe_in_place(items):
        seen_items = set()
        write_index = 0
        for read_index in range(len(items)):
            if items[read_index] not in seen_items:
                seen_items.add(items[read_index])
                items[write_index] = items[read_index]
                write_index += 1
        del items[write_index:]`,
  javascript: `class FrequencyCounter {
  constructor() {
    this.countByItem = new Map();
  }

  add(item) {
    this.countByItem.set(item, (this.countByItem.get(item) ?? 0) + 1);
  }

  count(item) {
    return this.countByItem.get(item) ?? 0;
  }

  mostCommon(limit) {
    return [...this.countByItem.entries()]
      .sort((leftEntry, rightEntry) => rightEntry[1] - leftEntry[1])
      .slice(0, limit);
  }

  decrement(item) {
    const currentCount = this.countByItem.get(item) ?? 0;
    if (currentCount <= 1) this.countByItem.delete(item);
    else this.countByItem.set(item, currentCount - 1);
  }
}

class SetToolkit {
  static hasDuplicate(items) {
    return new Set(items).size !== items.length;
  }

  static stableIntersection(firstItems, secondItems) {
    const secondSet = new Set(secondItems);
    return [...new Set(firstItems)].filter((item) => secondSet.has(item));
  }

  static dedupeInPlace(items) {
    const seenItems = new Set();
    let writeIndex = 0;
    for (let readIndex = 0; readIndex < items.length; readIndex += 1) {
      if (!seenItems.has(items[readIndex])) {
        seenItems.add(items[readIndex]);
        items[writeIndex] = items[readIndex];
        writeIndex += 1;
      }
    }
    items.length = writeIndex;
  }
}`,
  java: `import java.util.*;

class FrequencyCounter<T> {
    private final Map<T, Integer> countByItem = new HashMap<>();

    void add(T item) {
        countByItem.merge(item, 1, Integer::sum);
    }

    int count(T item) {
        return countByItem.getOrDefault(item, 0);
    }

    List<Map.Entry<T, Integer>> mostCommon(int limit) {
        return countByItem.entrySet().stream()
            .sorted((leftEntry, rightEntry) -> rightEntry.getValue() - leftEntry.getValue())
            .limit(limit)
            .toList();
    }

    void decrement(T item) {
        int currentCount = countByItem.getOrDefault(item, 0);
        if (currentCount <= 1) countByItem.remove(item);
        else countByItem.put(item, currentCount - 1);
    }
}

class SetToolkit {
    static <T> boolean hasDuplicate(List<T> items) {
        return new HashSet<>(items).size() != items.size();
    }

    static <T> List<T> stableIntersection(List<T> firstItems, List<T> secondItems) {
        Set<T> secondSet = new HashSet<>(secondItems);
        List<T> result = new ArrayList<>();
        Set<T> seenInFirst = new LinkedHashSet<>();
        for (T item : firstItems) {
            if (seenInFirst.add(item) && secondSet.contains(item)) result.add(item);
        }
        return result;
    }

    static <T> void dedupeInPlace(List<T> items) {
        Set<T> seenItems = new LinkedHashSet<>();
        int writeIndex = 0;
        for (int readIndex = 0; readIndex < items.size(); readIndex++) {
            T item = items.get(readIndex);
            if (seenItems.add(item)) {
                items.set(writeIndex, item);
                writeIndex += 1;
            }
        }
        items.subList(writeIndex, items.size()).clear();
    }
}`,
};

const MIN_HEAP_IMPL: Record<'python' | 'javascript' | 'java', string> = {
  python: `import heapq

class MinHeap:
    def __init__(self):
        self.values = []

    def push(self, value):
        heapq.heappush(self.values, value)

    def pop(self):
        return heapq.heappop(self.values) if self.values else None

    def peek(self):
        return self.values[0] if self.values else None

    def keep_largest_k(self, value, limit):
        heapq.heappush(self.values, value)
        if len(self.values) > limit:
            heapq.heappop(self.values)

    def merge_k_sorted_streams(self, streams):
        result = []
        min_heap = []
        for stream_index, stream in enumerate(streams):
            iterator = iter(stream)
            first_value = next(iterator, None)
            if first_value is not None:
                heapq.heappush(min_heap, (first_value, stream_index, iterator))
        while min_heap:
            current_value, stream_index, iterator = heapq.heappop(min_heap)
            result.append(current_value)
            next_value = next(iterator, None)
            if next_value is not None:
                heapq.heappush(min_heap, (next_value, stream_index, iterator))
        return result

    def __len__(self):
        return len(self.values)`,
  javascript: `class MinHeap {
  constructor(comesBefore = (leftValue, rightValue) => leftValue < rightValue) {
    this.values = [];
    this.comesBefore = comesBefore;
  }

  push(value) {
    this.values.push(value);
    this._bubbleUp(this.values.length - 1);
  }

  pop() {
    if (this.values.length === 0) return undefined;
    const topValue = this.values[0];
    const lastValue = this.values.pop();
    if (this.values.length > 0) {
      this.values[0] = lastValue;
      this._bubbleDown(0);
    }
    return topValue;
  }

  peek() {
    return this.values[0];
  }

  keepLargestK(value, limit) {
    this.push(value);
    if (this.values.length > limit) this.pop();
  }

  static mergeKSortedStreams(streams) {
    const result = [];
    const minHeap = new MinHeap((leftEntry, rightEntry) => leftEntry.value < rightEntry.value);
    for (let streamIndex = 0; streamIndex < streams.length; streamIndex += 1) {
      const stream = streams[streamIndex];
      if (stream.length > 0) {
        minHeap.push({ value: stream[0], streamIndex, itemIndex: 0 });
      }
    }
    while (minHeap.values.length > 0) {
      const { value: currentValue, streamIndex, itemIndex } = minHeap.pop();
      result.push(currentValue);
      const nextItemIndex = itemIndex + 1;
      if (nextItemIndex < streams[streamIndex].length) {
        minHeap.push({ value: streams[streamIndex][nextItemIndex], streamIndex, itemIndex: nextItemIndex });
      }
    }
    return result;
  }

  _bubbleUp(index) {
    let childIndex = index;
    while (childIndex > 0) {
      const parentIndex = Math.floor((childIndex - 1) / 2);
      if (!this.comesBefore(this.values[childIndex], this.values[parentIndex])) break;
      [this.values[childIndex], this.values[parentIndex]] = [this.values[parentIndex], this.values[childIndex]];
      childIndex = parentIndex;
    }
  }

  _bubbleDown(index) {
    let parentIndex = index;
    while (true) {
      const leftChildIndex = parentIndex * 2 + 1;
      const rightChildIndex = parentIndex * 2 + 2;
      let bestIndex = parentIndex;
      if (leftChildIndex < this.values.length && this.comesBefore(this.values[leftChildIndex], this.values[bestIndex])) bestIndex = leftChildIndex;
      if (rightChildIndex < this.values.length && this.comesBefore(this.values[rightChildIndex], this.values[bestIndex])) bestIndex = rightChildIndex;
      if (bestIndex === parentIndex) break;
      [this.values[parentIndex], this.values[bestIndex]] = [this.values[bestIndex], this.values[parentIndex]];
      parentIndex = bestIndex;
    }
  }
}`,
  java: `import java.util.*;

class MinHeap<T> {
    private final List<T> values = new ArrayList<>();
    private final Comparator<T> comparator;

    MinHeap(Comparator<T> comparator) {
        this.comparator = comparator;
    }

    void push(T value) {
        values.add(value);
        bubbleUp(values.size() - 1);
    }

    T pop() {
        if (values.isEmpty()) return null;
        T topValue = values.get(0);
        T lastValue = values.remove(values.size() - 1);
        if (!values.isEmpty()) {
            values.set(0, lastValue);
            bubbleDown(0);
        }
        return topValue;
    }

    T peek() {
        return values.isEmpty() ? null : values.get(0);
    }

    void keepLargestK(T value, int limit) {
        push(value);
        if (values.size() > limit) pop();
    }

    static List<Integer> mergeKSortedStreams(List<List<Integer>> streams) {
        List<Integer> result = new ArrayList<>();
        PriorityQueue<int[]> minHeap = new PriorityQueue<>(Comparator.comparingInt(entry -> entry[0]));
        for (int streamIndex = 0; streamIndex < streams.size(); streamIndex++) {
            List<Integer> stream = streams.get(streamIndex);
            if (!stream.isEmpty()) {
                minHeap.offer(new int[] { stream.get(0), streamIndex, 0 });
            }
        }
        while (!minHeap.isEmpty()) {
            int[] entry = minHeap.poll();
            int currentValue = entry[0];
            int streamIndex = entry[1];
            int itemIndex = entry[2];
            result.add(currentValue);
            int nextItemIndex = itemIndex + 1;
            if (nextItemIndex < streams.get(streamIndex).size()) {
                minHeap.offer(new int[] { streams.get(streamIndex).get(nextItemIndex), streamIndex, nextItemIndex });
            }
        }
        return result;
    }

    private void bubbleUp(int index) {
        int childIndex = index;
        while (childIndex > 0) {
            int parentIndex = (childIndex - 1) / 2;
            if (comparator.compare(values.get(childIndex), values.get(parentIndex)) >= 0) break;
            Collections.swap(values, childIndex, parentIndex);
            childIndex = parentIndex;
        }
    }

    private void bubbleDown(int index) {
        int parentIndex = index;
        while (true) {
            int leftChildIndex = parentIndex * 2 + 1;
            int rightChildIndex = parentIndex * 2 + 2;
            int bestIndex = parentIndex;
            if (leftChildIndex < values.size() && comparator.compare(values.get(leftChildIndex), values.get(bestIndex)) < 0) bestIndex = leftChildIndex;
            if (rightChildIndex < values.size() && comparator.compare(values.get(rightChildIndex), values.get(bestIndex)) < 0) bestIndex = rightChildIndex;
            if (bestIndex == parentIndex) break;
            Collections.swap(values, parentIndex, bestIndex);
            parentIndex = bestIndex;
        }
    }
}`,
};

const BINARY_TREE_IMPL: Record<'python' | 'javascript' | 'java', string> = {
  python: `from collections import deque

class TreeNode:
    def __init__(self, value, left=None, right=None):
        self.value = value
        self.left = left
        self.right = right

class BinaryTree:
    def __init__(self, root=None):
        self.root = root

    def in_order(self):
        result_values = []
        def visit(node):
            if node is None:
                return
            visit(node.left)
            result_values.append(node.value)
            visit(node.right)
        visit(self.root)
        return result_values

    def pre_order(self):
        result_values = []
        def visit(node):
            if node is None:
                return
            result_values.append(node.value)
            visit(node.left)
            visit(node.right)
        visit(self.root)
        return result_values

    def post_order(self):
        result_values = []
        def visit(node):
            if node is None:
                return
            visit(node.left)
            visit(node.right)
            result_values.append(node.value)
        visit(self.root)
        return result_values

    def level_order(self):
        if self.root is None:
            return []
        result_levels = []
        current_level_queue = deque([self.root])
        while current_level_queue:
            level_size = len(current_level_queue)
            level_values = []
            for _ in range(level_size):
                current_node = current_level_queue.popleft()
                level_values.append(current_node.value)
                if current_node.left is not None:
                    current_level_queue.append(current_node.left)
                if current_node.right is not None:
                    current_level_queue.append(current_node.right)
            result_levels.append(level_values)
        return result_levels

    def max_depth(self):
        def depth_of(node):
            if node is None:
                return 0
            return 1 + max(depth_of(node.left), depth_of(node.right))
        return depth_of(self.root)

    def lowest_common_ancestor(self, first_value, second_value):
        def find_lca(node):
            if node is None:
                return None
            if node.value == first_value or node.value == second_value:
                return node
            left_result = find_lca(node.left)
            right_result = find_lca(node.right)
            if left_result is not None and right_result is not None:
                return node
            return left_result if left_result is not None else right_result
        return find_lca(self.root)

    def serialize(self):
        tokens = []
        queue = deque([self.root])
        while queue:
            current_node = queue.popleft()
            if current_node is None:
                tokens.append('null')
            else:
                tokens.append(str(current_node.value))
                queue.append(current_node.left)
                queue.append(current_node.right)
        return ','.join(tokens)

    @classmethod
    def deserialize(cls, data):
        tokens = data.split(',')
        if not tokens or tokens[0] == 'null':
            return cls()
        root_node = TreeNode(int(tokens[0]))
        queue = deque([root_node])
        token_index = 1
        while queue and token_index < len(tokens):
            current_node = queue.popleft()
            left_token = tokens[token_index]
            token_index += 1
            if left_token != 'null':
                current_node.left = TreeNode(int(left_token))
                queue.append(current_node.left)
            if token_index < len(tokens):
                right_token = tokens[token_index]
                token_index += 1
                if right_token != 'null':
                    current_node.right = TreeNode(int(right_token))
                    queue.append(current_node.right)
        return cls(root_node)`,
  javascript: `class TreeNode {
  constructor(value, left = null, right = null) {
    this.value = value;
    this.left = left;
    this.right = right;
  }
}

class BinaryTree {
  constructor(root = null) {
    this.root = root;
  }

  inOrder() {
    const resultValues = [];
    const visit = (node) => {
      if (!node) return;
      visit(node.left);
      resultValues.push(node.value);
      visit(node.right);
    };
    visit(this.root);
    return resultValues;
  }

  preOrder() {
    const resultValues = [];
    const visit = (node) => {
      if (!node) return;
      resultValues.push(node.value);
      visit(node.left);
      visit(node.right);
    };
    visit(this.root);
    return resultValues;
  }

  postOrder() {
    const resultValues = [];
    const visit = (node) => {
      if (!node) return;
      visit(node.left);
      visit(node.right);
      resultValues.push(node.value);
    };
    visit(this.root);
    return resultValues;
  }

  levelOrder() {
    if (!this.root) return [];
    const resultLevels = [];
    const currentLevelQueue = [this.root];
    for (let queueStart = 0; queueStart < currentLevelQueue.length; ) {
      const levelSize = currentLevelQueue.length - queueStart;
      const levelValues = [];
      for (let i = 0; i < levelSize; i += 1) {
        const currentNode = currentLevelQueue[queueStart + i];
        levelValues.push(currentNode.value);
        if (currentNode.left) currentLevelQueue.push(currentNode.left);
        if (currentNode.right) currentLevelQueue.push(currentNode.right);
      }
      resultLevels.push(levelValues);
      queueStart += levelSize;
    }
    return resultLevels;
  }

  maxDepth(node = this.root) {
    if (!node) return 0;
    return 1 + Math.max(this.maxDepth(node.left), this.maxDepth(node.right));
  }

  lowestCommonAncestor(firstValue, secondValue) {
    const findLca = (node) => {
      if (!node) return null;
      if (node.value === firstValue || node.value === secondValue) return node;
      const leftResult = findLca(node.left);
      const rightResult = findLca(node.right);
      if (leftResult && rightResult) return node;
      return leftResult ?? rightResult;
    };
    return findLca(this.root);
  }

  serialize() {
    const tokens = [];
    const queue = [this.root];
    for (let queueIndex = 0; queueIndex < queue.length; queueIndex += 1) {
      const currentNode = queue[queueIndex];
      if (currentNode === null) {
        tokens.push('null');
      } else {
        tokens.push(String(currentNode.value));
        queue.push(currentNode.left);
        queue.push(currentNode.right);
      }
    }
    return tokens.join(',');
  }

  static deserialize(data) {
    const tokens = data.split(',');
    if (!tokens.length || tokens[0] === 'null') return new BinaryTree();
    const rootNode = new TreeNode(Number(tokens[0]));
    const queue = [rootNode];
    let tokenIndex = 1;
    for (let queueIndex = 0; queueIndex < queue.length && tokenIndex < tokens.length; queueIndex += 1) {
      const currentNode = queue[queueIndex];
      const leftToken = tokens[tokenIndex++];
      if (leftToken !== 'null') {
        currentNode.left = new TreeNode(Number(leftToken));
        queue.push(currentNode.left);
      }
      if (tokenIndex < tokens.length) {
        const rightToken = tokens[tokenIndex++];
        if (rightToken !== 'null') {
          currentNode.right = new TreeNode(Number(rightToken));
          queue.push(currentNode.right);
        }
      }
    }
    return new BinaryTree(rootNode);
  }
}`,
  java: `import java.util.*;

class BinaryTree<T> {
    static class TreeNode<T> {
        T value;
        TreeNode<T> left;
        TreeNode<T> right;
        TreeNode(T value) { this.value = value; }
    }

    TreeNode<T> root;

    BinaryTree(TreeNode<T> root) { this.root = root; }

    List<T> inOrder() {
        List<T> resultValues = new ArrayList<>();
        visitInOrder(root, resultValues);
        return resultValues;
    }

    private void visitInOrder(TreeNode<T> node, List<T> resultValues) {
        if (node == null) return;
        visitInOrder(node.left, resultValues);
        resultValues.add(node.value);
        visitInOrder(node.right, resultValues);
    }

    List<T> preOrder() {
        List<T> resultValues = new ArrayList<>();
        visitPreOrder(root, resultValues);
        return resultValues;
    }

    private void visitPreOrder(TreeNode<T> node, List<T> resultValues) {
        if (node == null) return;
        resultValues.add(node.value);
        visitPreOrder(node.left, resultValues);
        visitPreOrder(node.right, resultValues);
    }

    List<T> postOrder() {
        List<T> resultValues = new ArrayList<>();
        visitPostOrder(root, resultValues);
        return resultValues;
    }

    private void visitPostOrder(TreeNode<T> node, List<T> resultValues) {
        if (node == null) return;
        visitPostOrder(node.left, resultValues);
        visitPostOrder(node.right, resultValues);
        resultValues.add(node.value);
    }

    List<List<T>> levelOrder() {
        if (root == null) return List.of();
        List<List<T>> resultLevels = new ArrayList<>();
        Queue<TreeNode<T>> queue = new ArrayDeque<>();
        queue.offer(root);
        while (!queue.isEmpty()) {
            int levelSize = queue.size();
            List<T> levelValues = new ArrayList<>();
            for (int i = 0; i < levelSize; i++) {
                TreeNode<T> currentNode = queue.poll();
                levelValues.add(currentNode.value);
                if (currentNode.left != null) queue.offer(currentNode.left);
                if (currentNode.right != null) queue.offer(currentNode.right);
            }
            resultLevels.add(levelValues);
        }
        return resultLevels;
    }

    int maxDepth() {
        return depthOf(root);
    }

    private int depthOf(TreeNode<T> node) {
        if (node == null) return 0;
        return 1 + Math.max(depthOf(node.left), depthOf(node.right));
    }

    TreeNode<T> lowestCommonAncestor(T firstValue, T secondValue) {
        return findLca(root, firstValue, secondValue);
    }

    private TreeNode<T> findLca(TreeNode<T> node, T firstValue, T secondValue) {
        if (node == null) return null;
        if (node.value.equals(firstValue) || node.value.equals(secondValue)) return node;
        TreeNode<T> leftResult = findLca(node.left, firstValue, secondValue);
        TreeNode<T> rightResult = findLca(node.right, firstValue, secondValue);
        if (leftResult != null && rightResult != null) return node;
        return leftResult != null ? leftResult : rightResult;
    }

    String serialize() {
        StringBuilder tokens = new StringBuilder();
        Queue<TreeNode<T>> queue = new ArrayDeque<>();
        queue.offer(root);
        while (!queue.isEmpty()) {
            TreeNode<T> currentNode = queue.poll();
            if (tokens.length() > 0) tokens.append(',');
            if (currentNode == null) {
                tokens.append("null");
            } else {
                tokens.append(currentNode.value);
                queue.offer(currentNode.left);
                queue.offer(currentNode.right);
            }
        }
        return tokens.toString();
    }

    static BinaryTree<Integer> deserialize(String data) {
        String[] tokens = data.split(",");
        if (tokens.length == 0 || tokens[0].equals("null")) return new BinaryTree<>(null);
        TreeNode<Integer> rootNode = new TreeNode<>(Integer.parseInt(tokens[0]));
        Queue<TreeNode<Integer>> queue = new ArrayDeque<>();
        queue.offer(rootNode);
        int tokenIndex = 1;
        while (!queue.isEmpty() && tokenIndex < tokens.length) {
            TreeNode<Integer> currentNode = queue.poll();
            String leftToken = tokens[tokenIndex++];
            if (!leftToken.equals("null")) {
                currentNode.left = new TreeNode<>(Integer.parseInt(leftToken));
                queue.offer(currentNode.left);
            }
            if (tokenIndex < tokens.length) {
                String rightToken = tokens[tokenIndex++];
                if (!rightToken.equals("null")) {
                    currentNode.right = new TreeNode<>(Integer.parseInt(rightToken));
                    queue.offer(currentNode.right);
                }
            }
        }
        return new BinaryTree<>(rootNode);
    }
}`,
};

const TRIE_IMPL: Record<'python' | 'javascript' | 'java', string> = {
  python: `class TrieNode:
    def __init__(self):
        self.children_by_character = {}
        self.is_end_of_word = False

class Trie:
    def __init__(self):
        self.root_node = TrieNode()

    def insert(self, word):
        current_node = self.root_node
        for character in word:
            if character not in current_node.children_by_character:
                current_node.children_by_character[character] = TrieNode()
            current_node = current_node.children_by_character[character]
        current_node.is_end_of_word = True

    def contains(self, word):
        current_node = self.root_node
        for character in word:
            if character not in current_node.children_by_character:
                return False
            current_node = current_node.children_by_character[character]
        return current_node.is_end_of_word

    def starts_with(self, prefix):
        current_node = self.root_node
        for character in prefix:
            if character not in current_node.children_by_character:
                return False
            current_node = current_node.children_by_character[character]
        return True

    def words_with_prefix(self, prefix):
        current_node = self.root_node
        for character in prefix:
            if character not in current_node.children_by_character:
                return []
            current_node = current_node.children_by_character[character]
        matching_words = []
        def collect(node, built_prefix):
            if node.is_end_of_word:
                matching_words.append(built_prefix)
            for character, child_node in node.children_by_character.items():
                collect(child_node, built_prefix + character)
        collect(current_node, prefix)
        return matching_words`,
  javascript: `class TrieNode {
  constructor() {
    this.childrenByCharacter = new Map();
    this.isEndOfWord = false;
  }
}

class Trie {
  constructor() {
    this.rootNode = new TrieNode();
  }

  insert(word) {
    let currentNode = this.rootNode;
    for (const character of word) {
      if (!currentNode.childrenByCharacter.has(character)) {
        currentNode.childrenByCharacter.set(character, new TrieNode());
      }
      currentNode = currentNode.childrenByCharacter.get(character);
    }
    currentNode.isEndOfWord = true;
  }

  contains(word) {
    let currentNode = this.rootNode;
    for (const character of word) {
      if (!currentNode.childrenByCharacter.has(character)) return false;
      currentNode = currentNode.childrenByCharacter.get(character);
    }
    return currentNode.isEndOfWord;
  }

  startsWith(prefix) {
    let currentNode = this.rootNode;
    for (const character of prefix) {
      if (!currentNode.childrenByCharacter.has(character)) return false;
      currentNode = currentNode.childrenByCharacter.get(character);
    }
    return true;
  }

  wordsWithPrefix(prefix) {
    let currentNode = this.rootNode;
    for (const character of prefix) {
      if (!currentNode.childrenByCharacter.has(character)) return [];
      currentNode = currentNode.childrenByCharacter.get(character);
    }
    const matchingWords = [];
    const collect = (node, builtPrefix) => {
      if (node.isEndOfWord) matchingWords.push(builtPrefix);
      for (const [character, childNode] of node.childrenByCharacter) {
        collect(childNode, builtPrefix + character);
      }
    };
    collect(currentNode, prefix);
    return matchingWords;
  }
}`,
  java: `import java.util.*;

class Trie {
    private static class TrieNode {
        final Map<Character, TrieNode> childrenByCharacter = new HashMap<>();
        boolean isEndOfWord = false;
    }

    private final TrieNode rootNode = new TrieNode();

    void insert(String word) {
        TrieNode currentNode = rootNode;
        for (char character : word.toCharArray()) {
            currentNode.childrenByCharacter.putIfAbsent(character, new TrieNode());
            currentNode = currentNode.childrenByCharacter.get(character);
        }
        currentNode.isEndOfWord = true;
    }

    boolean contains(String word) {
        TrieNode currentNode = rootNode;
        for (char character : word.toCharArray()) {
            if (!currentNode.childrenByCharacter.containsKey(character)) return false;
            currentNode = currentNode.childrenByCharacter.get(character);
        }
        return currentNode.isEndOfWord;
    }

    boolean startsWith(String prefix) {
        TrieNode currentNode = rootNode;
        for (char character : prefix.toCharArray()) {
            if (!currentNode.childrenByCharacter.containsKey(character)) return false;
            currentNode = currentNode.childrenByCharacter.get(character);
        }
        return true;
    }

    List<String> wordsWithPrefix(String prefix) {
        TrieNode currentNode = rootNode;
        for (char character : prefix.toCharArray()) {
            if (!currentNode.childrenByCharacter.containsKey(character)) return List.of();
            currentNode = currentNode.childrenByCharacter.get(character);
        }
        List<String> matchingWords = new ArrayList<>();
        collectWords(currentNode, new StringBuilder(prefix), matchingWords);
        return matchingWords;
    }

    private void collectWords(TrieNode node, StringBuilder builtPrefix, List<String> matchingWords) {
        if (node.isEndOfWord) matchingWords.add(builtPrefix.toString());
        for (Map.Entry<Character, TrieNode> entry : node.childrenByCharacter.entrySet()) {
            builtPrefix.append(entry.getKey());
            collectWords(entry.getValue(), builtPrefix, matchingWords);
            builtPrefix.deleteCharAt(builtPrefix.length() - 1);
        }
    }
}`,
};

const UNION_FIND_IMPL: Record<'python' | 'javascript' | 'java', string> = {
  python: `class UnionFind:
    def __init__(self):
        self.parent_by_item = {}
        self.size_by_root = {}

    def find(self, item):
        if item not in self.parent_by_item:
            self.parent_by_item[item] = item
            self.size_by_root[item] = 1
        if self.parent_by_item[item] != item:
            self.parent_by_item[item] = self.find(self.parent_by_item[item])
        return self.parent_by_item[item]

    def union(self, first_item, second_item):
        first_root = self.find(first_item)
        second_root = self.find(second_item)
        if first_root == second_root:
            return False
        if self.size_by_root[first_root] < self.size_by_root[second_root]:
            first_root, second_root = second_root, first_root
        self.parent_by_item[second_root] = first_root
        self.size_by_root[first_root] += self.size_by_root[second_root]
        return True

    def connected(self, first_item, second_item):
        return self.find(first_item) == self.find(second_item)

    def count_groups(self):
        return sum(
            1 for item in self.parent_by_item
            if self.parent_by_item[item] == item
        )`,
  javascript: `class UnionFind {
  constructor() {
    this.parentByItem = new Map();
    this.sizeByRoot = new Map();
  }

  find(item) {
    if (!this.parentByItem.has(item)) {
      this.parentByItem.set(item, item);
      this.sizeByRoot.set(item, 1);
    }
    const parent = this.parentByItem.get(item);
    if (parent === item) return item;
    const root = this.find(parent);
    this.parentByItem.set(item, root);
    return root;
  }

  union(firstItem, secondItem) {
    let firstRoot = this.find(firstItem);
    let secondRoot = this.find(secondItem);
    if (firstRoot === secondRoot) return false;
    if (this.sizeByRoot.get(firstRoot) < this.sizeByRoot.get(secondRoot)) {
      [firstRoot, secondRoot] = [secondRoot, firstRoot];
    }
    this.parentByItem.set(secondRoot, firstRoot);
    this.sizeByRoot.set(firstRoot, this.sizeByRoot.get(firstRoot) + this.sizeByRoot.get(secondRoot));
    return true;
  }

  connected(firstItem, secondItem) {
    return this.find(firstItem) === this.find(secondItem);
  }

  countGroups() {
    let groupCount = 0;
    for (const [item, parent] of this.parentByItem) {
      if (item === parent) groupCount += 1;
    }
    return groupCount;
  }
}`,
  java: `import java.util.*;

class UnionFind<T> {
    private final Map<T, T> parentByItem = new HashMap<>();
    private final Map<T, Integer> sizeByRoot = new HashMap<>();

    T find(T item) {
        parentByItem.putIfAbsent(item, item);
        sizeByRoot.putIfAbsent(item, 1);
        T parent = parentByItem.get(item);
        if (parent.equals(item)) return item;
        T root = find(parent);
        parentByItem.put(item, root);
        return root;
    }

    boolean union(T firstItem, T secondItem) {
        T firstRoot = find(firstItem);
        T secondRoot = find(secondItem);
        if (firstRoot.equals(secondRoot)) return false;
        if (sizeByRoot.get(firstRoot) < sizeByRoot.get(secondRoot)) {
            T temporaryRoot = firstRoot;
            firstRoot = secondRoot;
            secondRoot = temporaryRoot;
        }
        parentByItem.put(secondRoot, firstRoot);
        sizeByRoot.put(firstRoot, sizeByRoot.get(firstRoot) + sizeByRoot.get(secondRoot));
        return true;
    }

    boolean connected(T firstItem, T secondItem) {
        return find(firstItem).equals(find(secondItem));
    }

    int countGroups() {
        int groupCount = 0;
        for (Map.Entry<T, T> entry : parentByItem.entrySet()) {
            if (entry.getKey().equals(entry.getValue())) groupCount += 1;
        }
        return groupCount;
    }
}`,
};

const MONOTONIC_STACK_IMPL: Record<'python' | 'javascript' | 'java', string> = {
  python: `class MonotonicStack:
    def __init__(self):
        self.pending_values = []

    def push_with_resolve(self, value, on_resolve):
        while self.pending_values and self.pending_values[-1] < value:
            popped_value = self.pending_values.pop()
            on_resolve(popped_value, value)
        self.pending_values.append(value)

    @staticmethod
    def next_greater_indices(numbers):
        next_greater_index = [-1] * len(numbers)
        pending_indices = []
        for current_index, current_number in enumerate(numbers):
            while pending_indices and numbers[pending_indices[-1]] < current_number:
                resolved_index = pending_indices.pop()
                next_greater_index[resolved_index] = current_index
            pending_indices.append(current_index)
        return next_greater_index`,
  javascript: `class MonotonicStack {
  constructor() {
    this.pendingValues = [];
  }

  pushWithResolve(value, onResolve) {
    while (this.pendingValues.length > 0 && this.pendingValues[this.pendingValues.length - 1] < value) {
      const poppedValue = this.pendingValues.pop();
      onResolve(poppedValue, value);
    }
    this.pendingValues.push(value);
  }

  static nextGreaterIndices(numbers) {
    const nextGreaterIndex = new Array(numbers.length).fill(-1);
    const pendingIndices = [];
    for (let currentIndex = 0; currentIndex < numbers.length; currentIndex += 1) {
      const currentNumber = numbers[currentIndex];
      while (pendingIndices.length > 0 && numbers[pendingIndices[pendingIndices.length - 1]] < currentNumber) {
        const resolvedIndex = pendingIndices.pop();
        nextGreaterIndex[resolvedIndex] = currentIndex;
      }
      pendingIndices.push(currentIndex);
    }
    return nextGreaterIndex;
  }
}`,
  java: `import java.util.*;

class MonotonicStack {
    private final Deque<Integer> pendingValues = new ArrayDeque<>();

    void pushWithResolve(int value, java.util.function.BiConsumer<Integer, Integer> onResolve) {
        while (!pendingValues.isEmpty() && pendingValues.peek() < value) {
            int poppedValue = pendingValues.pop();
            onResolve.accept(poppedValue, value);
        }
        pendingValues.push(value);
    }

    static int[] nextGreaterIndices(int[] numbers) {
        int[] nextGreaterIndex = new int[numbers.length];
        Arrays.fill(nextGreaterIndex, -1);
        Deque<Integer> pendingIndices = new ArrayDeque<>();
        for (int currentIndex = 0; currentIndex < numbers.length; currentIndex++) {
            while (!pendingIndices.isEmpty() && numbers[pendingIndices.peek()] < numbers[currentIndex]) {
                int resolvedIndex = pendingIndices.pop();
                nextGreaterIndex[resolvedIndex] = currentIndex;
            }
            pendingIndices.push(currentIndex);
        }
        return nextGreaterIndex;
    }
}`,
};

const SLIDING_WINDOW_TOOLKIT_IMPL: Record<'python' | 'javascript' | 'java', string> = {
  python: `from collections import defaultdict

class SlidingWindowToolkit:
    @staticmethod
    def longest_with_at_most_k_distinct(text, k):
        counts_by_character = defaultdict(int)
        left_index = 0
        best_length = 0
        for right_index, added_character in enumerate(text):
            counts_by_character[added_character] += 1
            while len(counts_by_character) > k:
                removed_character = text[left_index]
                counts_by_character[removed_character] -= 1
                if counts_by_character[removed_character] == 0:
                    del counts_by_character[removed_character]
                left_index += 1
            best_length = max(best_length, right_index - left_index + 1)
        return best_length

    @staticmethod
    def longest_without_repeating(text):
        last_seen_index = {}
        left_index = 0
        best_length = 0
        for right_index, current_character in enumerate(text):
            if current_character in last_seen_index and last_seen_index[current_character] >= left_index:
                left_index = last_seen_index[current_character] + 1
            last_seen_index[current_character] = right_index
            best_length = max(best_length, right_index - left_index + 1)
        return best_length

    @staticmethod
    def min_window_with_chars(text, required):
        required_counts = defaultdict(int)
        for character in required:
            required_counts[character] += 1
        window_counts = defaultdict(int)
        satisfied_characters = 0
        needed_characters = len(required_counts)
        left_index = 0
        best_start = -1
        best_length = float('inf')
        for right_index, added_character in enumerate(text):
            window_counts[added_character] += 1
            if added_character in required_counts and window_counts[added_character] == required_counts[added_character]:
                satisfied_characters += 1
            while satisfied_characters == needed_characters:
                window_length = right_index - left_index + 1
                if window_length < best_length:
                    best_length = window_length
                    best_start = left_index
                removed_character = text[left_index]
                window_counts[removed_character] -= 1
                if removed_character in required_counts and window_counts[removed_character] < required_counts[removed_character]:
                    satisfied_characters -= 1
                left_index += 1
        return text[best_start:best_start + best_length] if best_start >= 0 else ''

    @staticmethod
    def max_sum_of_size_k(numbers, window_size):
        if len(numbers) < window_size:
            return 0
        window_sum = sum(numbers[:window_size])
        best_sum = window_sum
        for right_index in range(window_size, len(numbers)):
            window_sum += numbers[right_index] - numbers[right_index - window_size]
            best_sum = max(best_sum, window_sum)
        return best_sum`,
  javascript: `class SlidingWindowToolkit {
  static longestWithAtMostKDistinct(text, k) {
    const countsByCharacter = new Map();
    let leftIndex = 0;
    let bestLength = 0;
    for (let rightIndex = 0; rightIndex < text.length; rightIndex += 1) {
      const addedCharacter = text[rightIndex];
      countsByCharacter.set(addedCharacter, (countsByCharacter.get(addedCharacter) ?? 0) + 1);
      while (countsByCharacter.size > k) {
        const removedCharacter = text[leftIndex];
        const nextCount = countsByCharacter.get(removedCharacter) - 1;
        if (nextCount === 0) countsByCharacter.delete(removedCharacter);
        else countsByCharacter.set(removedCharacter, nextCount);
        leftIndex += 1;
      }
      bestLength = Math.max(bestLength, rightIndex - leftIndex + 1);
    }
    return bestLength;
  }

  static longestWithoutRepeating(text) {
    const lastSeenIndex = new Map();
    let leftIndex = 0;
    let bestLength = 0;
    for (let rightIndex = 0; rightIndex < text.length; rightIndex += 1) {
      const currentCharacter = text[rightIndex];
      const previousIndex = lastSeenIndex.get(currentCharacter);
      if (previousIndex !== undefined && previousIndex >= leftIndex) {
        leftIndex = previousIndex + 1;
      }
      lastSeenIndex.set(currentCharacter, rightIndex);
      bestLength = Math.max(bestLength, rightIndex - leftIndex + 1);
    }
    return bestLength;
  }

  static minWindowWithChars(text, required) {
    const requiredCounts = new Map();
    for (const character of required) {
      requiredCounts.set(character, (requiredCounts.get(character) ?? 0) + 1);
    }
    const windowCounts = new Map();
    let satisfiedCharacters = 0;
    const neededCharacters = requiredCounts.size;
    let leftIndex = 0;
    let bestStart = -1;
    let bestLength = Infinity;
    for (let rightIndex = 0; rightIndex < text.length; rightIndex += 1) {
      const addedCharacter = text[rightIndex];
      windowCounts.set(addedCharacter, (windowCounts.get(addedCharacter) ?? 0) + 1);
      if (requiredCounts.has(addedCharacter) && windowCounts.get(addedCharacter) === requiredCounts.get(addedCharacter)) {
        satisfiedCharacters += 1;
      }
      while (satisfiedCharacters === neededCharacters) {
        const windowLength = rightIndex - leftIndex + 1;
        if (windowLength < bestLength) {
          bestLength = windowLength;
          bestStart = leftIndex;
        }
        const removedCharacter = text[leftIndex];
        const nextCount = windowCounts.get(removedCharacter) - 1;
        windowCounts.set(removedCharacter, nextCount);
        if (requiredCounts.has(removedCharacter) && nextCount < requiredCounts.get(removedCharacter)) {
          satisfiedCharacters -= 1;
        }
        leftIndex += 1;
      }
    }
    return bestStart >= 0 ? text.slice(bestStart, bestStart + bestLength) : '';
  }

  static maxSumOfSizeK(numbers, windowSize) {
    if (numbers.length < windowSize) return 0;
    let windowSum = 0;
    for (let i = 0; i < windowSize; i += 1) windowSum += numbers[i];
    let bestSum = windowSum;
    for (let rightIndex = windowSize; rightIndex < numbers.length; rightIndex += 1) {
      windowSum += numbers[rightIndex] - numbers[rightIndex - windowSize];
      bestSum = Math.max(bestSum, windowSum);
    }
    return bestSum;
  }
}`,
  java: `import java.util.*;

class SlidingWindowToolkit {
    static int longestWithAtMostKDistinct(String text, int k) {
        Map<Character, Integer> countsByCharacter = new HashMap<>();
        int leftIndex = 0;
        int bestLength = 0;
        for (int rightIndex = 0; rightIndex < text.length(); rightIndex++) {
            char addedCharacter = text.charAt(rightIndex);
            countsByCharacter.merge(addedCharacter, 1, Integer::sum);
            while (countsByCharacter.size() > k) {
                char removedCharacter = text.charAt(leftIndex);
                int nextCount = countsByCharacter.merge(removedCharacter, -1, Integer::sum);
                if (nextCount == 0) countsByCharacter.remove(removedCharacter);
                leftIndex++;
            }
            bestLength = Math.max(bestLength, rightIndex - leftIndex + 1);
        }
        return bestLength;
    }

    static int longestWithoutRepeating(String text) {
        Map<Character, Integer> lastSeenIndex = new HashMap<>();
        int leftIndex = 0;
        int bestLength = 0;
        for (int rightIndex = 0; rightIndex < text.length(); rightIndex++) {
            char currentCharacter = text.charAt(rightIndex);
            if (lastSeenIndex.containsKey(currentCharacter) && lastSeenIndex.get(currentCharacter) >= leftIndex) {
                leftIndex = lastSeenIndex.get(currentCharacter) + 1;
            }
            lastSeenIndex.put(currentCharacter, rightIndex);
            bestLength = Math.max(bestLength, rightIndex - leftIndex + 1);
        }
        return bestLength;
    }

    static String minWindowWithChars(String text, String required) {
        Map<Character, Integer> requiredCounts = new HashMap<>();
        for (char character : required.toCharArray()) requiredCounts.merge(character, 1, Integer::sum);
        Map<Character, Integer> windowCounts = new HashMap<>();
        int satisfiedCharacters = 0;
        int neededCharacters = requiredCounts.size();
        int leftIndex = 0;
        int bestStart = -1;
        int bestLength = Integer.MAX_VALUE;
        for (int rightIndex = 0; rightIndex < text.length(); rightIndex++) {
            char addedCharacter = text.charAt(rightIndex);
            windowCounts.merge(addedCharacter, 1, Integer::sum);
            if (requiredCounts.containsKey(addedCharacter) &&
                    windowCounts.get(addedCharacter).equals(requiredCounts.get(addedCharacter))) {
                satisfiedCharacters++;
            }
            while (satisfiedCharacters == neededCharacters) {
                int windowLength = rightIndex - leftIndex + 1;
                if (windowLength < bestLength) {
                    bestLength = windowLength;
                    bestStart = leftIndex;
                }
                char removedCharacter = text.charAt(leftIndex);
                int nextCount = windowCounts.merge(removedCharacter, -1, Integer::sum);
                if (requiredCounts.containsKey(removedCharacter) && nextCount < requiredCounts.get(removedCharacter)) {
                    satisfiedCharacters--;
                }
                leftIndex++;
            }
        }
        return bestStart >= 0 ? text.substring(bestStart, bestStart + bestLength) : "";
    }

    static int maxSumOfSizeK(int[] numbers, int windowSize) {
        if (numbers.length < windowSize) return 0;
        int windowSum = 0;
        for (int i = 0; i < windowSize; i++) windowSum += numbers[i];
        int bestSum = windowSum;
        for (int rightIndex = windowSize; rightIndex < numbers.length; rightIndex++) {
            windowSum += numbers[rightIndex] - numbers[rightIndex - windowSize];
            bestSum = Math.max(bestSum, windowSum);
        }
        return bestSum;
    }
}`,
};

const CODE_KIT_SHELVES_PARTIAL: CodingContent['codeKit']['shelves'] = [
  {
    id: 'arrays',
    number: '01',
    name: 'ArrayToolkit',
    concepts: ['two pointers', 'sliding window', 'binary search', 'prefix thinking'],
    methods: [
      { name: 'binary_search',                       purpose: 'classic sorted-array lookup with the (l + (r-l)/2) midpoint pattern' },
      { name: 'find_pair_with_target',               purpose: 'first matching index pair using a one-pass hash map' },
      { name: 'longest_subarray_with_sum_at_most',   purpose: 'variable-size sliding window with a running sum' },
      { name: 'rotate_in_place',                     purpose: 'three-reverse trick for in-place k-rotation' },
      { name: 'sliding_window_max',                  purpose: 'monotonic deque returning the window max in O(n)' },
      { name: 'partition_around_pivot',              purpose: 'Lomuto partition used by quickselect' },
    ],
    implementations: ARRAY_TOOLKIT_IMPL,
  },
  {
    id: 'linked-lists',
    number: '02',
    name: 'SinglyLinkedList',
    concepts: ['dummy nodes', 'slow/fast pointers', 'reversal', 'cycle detection'],
    methods: [
      { name: 'append',               purpose: 'add a value to the tail; updates tail pointer' },
      { name: 'prepend',              purpose: 'add a value at the head; updates head pointer' },
      { name: 'reverse',              purpose: 'reverse the list in place; updates head and tail' },
      { name: 'find_middle',          purpose: 'slow/fast pointer; returns the middle node' },
      { name: 'has_cycle',            purpose: "Floyd's tortoise-and-hare cycle detection" },
      { name: 'find_cycle_start',     purpose: 'second-pass reset to find the cycle entry node' },
      { name: 'remove_nth_from_end',  purpose: 'single-pass with two pointers n+1 apart' },
      { name: 'merge_sorted',         purpose: 'merge another sorted list into this one with a dummy head' },
      { name: 'intersection_node',    purpose: 'find the node where two lists merge using pointer resets' },
    ],
    implementations: SINGLY_LINKED_LIST_IMPL,
  },
  {
    id: 'graphs',
    number: '03',
    name: 'Graph',
    concepts: ['adjacency list', 'BFS', 'DFS', 'visited set'],
    methods: [
      { name: 'add_undirected_edge',             purpose: 'add a bidirectional edge to the adjacency list' },
      { name: 'add_directed_edge',               purpose: 'add a one-way edge; ensures target node is registered' },
      { name: 'bfs',                             purpose: 'breadth-first traversal; returns nodes in level order' },
      { name: 'dfs',                             purpose: 'depth-first traversal; returns nodes in visit order' },
      { name: 'find_shortest_unweighted_path',   purpose: 'BFS-derived shortest path in an unweighted graph' },
      { name: 'count_components',                purpose: 'count connected components using iterative DFS' },
      { name: 'has_cycle_directed',              purpose: 'DFS with white/gray/black coloring to detect a directed cycle' },
      { name: 'topological_order',               purpose: "Kahn's algorithm (indegree queue); returns empty if cycle exists" },
    ],
    implementations: GRAPH_IMPL,
  },
  {
    id: 'maps-sets',
    number: '04',
    name: 'FrequencyCounter + SetToolkit',
    concepts: ['hash map', 'hash set', 'frequency counter', 'dedupe'],
    methods: [
      { name: 'FrequencyCounter.add',             purpose: 'increment count for an item by one' },
      { name: 'FrequencyCounter.count',           purpose: 'return current count for an item; zero if unseen' },
      { name: 'FrequencyCounter.most_common',     purpose: 'return the top-k items by descending frequency' },
      { name: 'FrequencyCounter.decrement',       purpose: 'decrement count; removes the item when count reaches zero' },
      { name: 'SetToolkit.has_duplicate',         purpose: 'returns true if any value appears more than once' },
      { name: 'SetToolkit.stable_intersection',   purpose: 'items in both collections, preserving first-collection order' },
      { name: 'SetToolkit.dedupe_in_place',       purpose: 'remove duplicates in place while preserving insertion order' },
    ],
    implementations: FREQUENCY_COUNTER_SET_TOOLKIT_IMPL,
  },
  {
    id: 'heaps',
    number: '05',
    name: 'MinHeap / PriorityQueue',
    concepts: ['min heap', 'comparator', 'top k', 'priority queue'],
    methods: [
      { name: 'push',                   purpose: 'insert a value and restore the heap property upward' },
      { name: 'pop',                    purpose: 'remove and return the minimum; restores heap property downward' },
      { name: 'peek',                   purpose: 'return the minimum without removing it' },
      { name: 'keep_largest_k',         purpose: 'push the value and pop the min if size exceeds k; keeps top-k largest' },
      { name: 'merge_k_sorted_streams', purpose: 'merge k sorted iterables in O(n log k) using a min-heap cursor per stream' },
    ],
    implementations: MIN_HEAP_IMPL,
  },
  {
    id: 'binary-tree',
    number: '06',
    name: 'BinaryTree',
    concepts: ['traversal', 'depth', 'recursion', 'serialization'],
    methods: [
      { name: 'in_order',                 purpose: 'left → root → right; yields sorted order for a BST' },
      { name: 'pre_order',                purpose: 'root → left → right; useful for tree cloning and serialization' },
      { name: 'post_order',               purpose: 'left → right → root; useful for deletion and bottom-up aggregation' },
      { name: 'level_order',              purpose: 'BFS by level; returns list of lists' },
      { name: 'max_depth',                purpose: 'recursive depth; 0 for null, 1 + max(left, right) otherwise' },
      { name: 'lowest_common_ancestor',   purpose: 'post-order search returning the first node that sees both targets' },
      { name: 'serialize',                purpose: 'level-order with null markers; produces a comma-separated string' },
      { name: 'deserialize',              purpose: 'rebuild the tree from the serialized level-order string' },
    ],
    implementations: BINARY_TREE_IMPL,
  },
  {
    id: 'trie',
    number: '07',
    name: 'Trie',
    concepts: ['prefix matching', 'autocomplete', 'word search'],
    methods: [
      { name: 'insert',             purpose: 'walk or create nodes for each character; mark the last as end-of-word' },
      { name: 'contains',          purpose: 'walk nodes for each character; return true only if end-of-word is set' },
      { name: 'starts_with',       purpose: 'walk nodes for each prefix character; return true if path exists' },
      { name: 'words_with_prefix', purpose: 'walk to prefix end, then DFS to collect all complete words below' },
    ],
    implementations: TRIE_IMPL,
  },
  {
    id: 'union-find',
    number: '08',
    name: 'UnionFind',
    concepts: ['path compression', 'union by size', 'connectivity'],
    methods: [
      { name: 'find',         purpose: 'return the root representative; path-compresses on the way up' },
      { name: 'union',        purpose: 'merge two groups by attaching the smaller root to the larger' },
      { name: 'connected',    purpose: 'returns true if find(a) === find(b) — same component' },
      { name: 'count_groups', purpose: 'count distinct roots — the number of independent components' },
    ],
    implementations: UNION_FIND_IMPL,
  },
  {
    id: 'monotonic-stack',
    number: '09',
    name: 'MonotonicStack',
    concepts: ['next greater', 'next smaller', 'span', 'histogram'],
    methods: [
      { name: 'push_with_resolve',    purpose: 'push onto a monotonic decreasing stack; fires on_resolve for each popped value' },
      { name: 'next_greater_indices', purpose: 'static: returns index of next greater element for each position, or -1' },
    ],
    implementations: MONOTONIC_STACK_IMPL,
  },
  {
    id: 'sliding-window-toolkit',
    number: '10',
    name: 'SlidingWindowToolkit',
    concepts: ['variable window', 'fixed window', 'character frequency'],
    methods: [
      { name: 'longest_with_at_most_k_distinct',  purpose: 'variable window with a character frequency map; shrinks when distinct > k' },
      { name: 'longest_without_repeating',        purpose: 'variable window with a last-seen index map; jumps left past the duplicate' },
      { name: 'min_window_with_chars',            purpose: 'minimum window substring; tracks satisfied character counts' },
      { name: 'max_sum_of_size_k',               purpose: 'fixed-size sliding window sum; O(n) with a single running total' },
    ],
    implementations: SLIDING_WINDOW_TOOLKIT_IMPL,
  },
];

const PATTERN_ENTRIES_PARTIAL: CodingContent['patterns']['entries'] = [
  // Task 2.3 will append 15 more pattern entries.
  {
    id: 'pat-two-pointers',
    family: 'linear',
    title: 'Two Pointers',
    trigger: 'sorted input + pair/triplet/partition pressure',
    state: 'l < r preserves the sorted invariant; moving l grows sum, moving r shrinks it',
    watch: 'sort first when input is unsorted; skip duplicates explicitly',
    skeletons: {
      python: `def two_pointer_pair_sum(sorted_numbers, target_sum):
    left_index, right_index = 0, len(sorted_numbers) - 1
    while left_index < right_index:
        current_sum = sorted_numbers[left_index] + sorted_numbers[right_index]
        if current_sum == target_sum:
            return (left_index, right_index)
        if current_sum < target_sum:
            left_index += 1
        else:
            right_index -= 1
    return None`,
      javascript: `function twoPointerPairSum(sortedNumbers, targetSum) {
  let leftIndex = 0;
  let rightIndex = sortedNumbers.length - 1;
  while (leftIndex < rightIndex) {
    const currentSum = sortedNumbers[leftIndex] + sortedNumbers[rightIndex];
    if (currentSum === targetSum) return [leftIndex, rightIndex];
    if (currentSum < targetSum) leftIndex += 1;
    else rightIndex -= 1;
  }
  return null;
}`,
      java: `int[] twoPointerPairSum(int[] sortedNumbers, int targetSum) {
    int leftIndex = 0;
    int rightIndex = sortedNumbers.length - 1;
    while (leftIndex < rightIndex) {
        int currentSum = sortedNumbers[leftIndex] + sortedNumbers[rightIndex];
        if (currentSum == targetSum) return new int[] { leftIndex, rightIndex };
        if (currentSum < targetSum) leftIndex++; else rightIndex--;
    }
    return new int[] {};
}`,
    },
  },
  {
    id: 'pat-sliding-fixed',
    family: 'linear',
    title: 'Sliding Window — fixed size',
    trigger: 'exactly-k subarray max, sum, product, or count',
    state: 'window [r-k+1, r] always has exactly k elements; runningSum updated by add/subtract',
    watch: 'return early if input length is less than k — no valid window exists',
    skeletons: {
      python: `def fixed_window(numbers, window_size):
    if len(numbers) < window_size:
        return []          # or 0 / None depending on problem
    window_sum = sum(numbers[:window_size])
    best_result = window_sum  # or collect into a list
    for right_index in range(window_size, len(numbers)):
        window_sum += numbers[right_index]
        window_sum -= numbers[right_index - window_size]
        best_result = max(best_result, window_sum)
    return best_result`,
      javascript: `function fixedWindow(numbers, windowSize) {
  if (numbers.length < windowSize) return [];
  let windowSum = 0;
  for (let i = 0; i < windowSize; i += 1) windowSum += numbers[i];
  let bestResult = windowSum;
  for (let rightIndex = windowSize; rightIndex < numbers.length; rightIndex += 1) {
    windowSum += numbers[rightIndex];
    windowSum -= numbers[rightIndex - windowSize];
    bestResult = Math.max(bestResult, windowSum);
  }
  return bestResult;
}`,
      java: `int fixedWindow(int[] numbers, int windowSize) {
    if (numbers.length < windowSize) return 0;
    int windowSum = 0;
    for (int i = 0; i < windowSize; i++) windowSum += numbers[i];
    int bestResult = windowSum;
    for (int rightIndex = windowSize; rightIndex < numbers.length; rightIndex++) {
        windowSum += numbers[rightIndex];
        windowSum -= numbers[rightIndex - windowSize];
        bestResult = Math.max(bestResult, windowSum);
    }
    return bestResult;
}`,
    },
  },
  {
    id: 'pat-sliding-variable',
    family: 'linear',
    title: 'Sliding Window — variable size',
    trigger: 'longest or shortest contiguous range satisfying a condition',
    state: 'window [leftIndex, rightIndex] is the largest valid range ending at rightIndex',
    watch: 'with negative numbers, sum-based variable window fails — switch to prefix sums',
    skeletons: {
      python: `def variable_window(numbers, condition_limit):
    left_index = 0
    window_state = 0   # e.g. running sum, count, or frequency map
    best_length = 0
    for right_index, added_value in enumerate(numbers):
        window_state += added_value            # expand: update state
        while not is_valid(window_state, condition_limit):
            window_state -= numbers[left_index]  # shrink: undo left
            left_index += 1
        best_length = max(best_length, right_index - left_index + 1)
    return best_length`,
      javascript: `function variableWindow(numbers, conditionLimit) {
  let leftIndex = 0;
  let windowState = 0;  // running sum, count, or Map
  let bestLength = 0;
  for (let rightIndex = 0; rightIndex < numbers.length; rightIndex += 1) {
    windowState += numbers[rightIndex];            // expand
    while (!isValid(windowState, conditionLimit)) {
      windowState -= numbers[leftIndex];           // shrink
      leftIndex += 1;
    }
    bestLength = Math.max(bestLength, rightIndex - leftIndex + 1);
  }
  return bestLength;
}`,
      java: `int variableWindow(int[] numbers, int conditionLimit) {
    int leftIndex = 0;
    int windowState = 0;
    int bestLength = 0;
    for (int rightIndex = 0; rightIndex < numbers.length; rightIndex++) {
        windowState += numbers[rightIndex];           // expand
        while (!isValid(windowState, conditionLimit)) {
            windowState -= numbers[leftIndex];        // shrink
            leftIndex++;
        }
        bestLength = Math.max(bestLength, rightIndex - leftIndex + 1);
    }
    return bestLength;
}`,
    },
  },
  {
    id: 'pat-prefix-sum',
    family: 'linear',
    title: 'Prefix Sum',
    trigger: 'range totals, subarray equals k, immutable repeated range queries',
    state: 'prefixSum[i] = sum of numbers[0..i-1]; range [l,r] = prefixSum[r+1] - prefixSum[l]',
    watch: 'initialize count[0] = 1 before the loop so subarrays starting at index 0 are counted',
    skeletons: {
      python: `def count_subarrays_with_sum(numbers, target_sum):
    count_by_prefix = {0: 1}
    running_sum = 0
    total_count = 0
    for current_number in numbers:
        running_sum += current_number
        needed_prefix = running_sum - target_sum
        total_count += count_by_prefix.get(needed_prefix, 0)
        count_by_prefix[running_sum] = count_by_prefix.get(running_sum, 0) + 1
    return total_count`,
      javascript: `function countSubarraysWithSum(numbers, targetSum) {
  const countByPrefix = new Map([[0, 1]]);
  let runningSum = 0;
  let totalCount = 0;
  for (const currentNumber of numbers) {
    runningSum += currentNumber;
    const neededPrefix = runningSum - targetSum;
    totalCount += countByPrefix.get(neededPrefix) ?? 0;
    countByPrefix.set(runningSum, (countByPrefix.get(runningSum) ?? 0) + 1);
  }
  return totalCount;
}`,
      java: `int countSubarraysWithSum(int[] numbers, int targetSum) {
    Map<Integer, Integer> countByPrefix = new HashMap<>();
    countByPrefix.put(0, 1);
    int runningSum = 0;
    int totalCount = 0;
    for (int currentNumber : numbers) {
        runningSum += currentNumber;
        int neededPrefix = runningSum - targetSum;
        totalCount += countByPrefix.getOrDefault(neededPrefix, 0);
        countByPrefix.merge(runningSum, 1, Integer::sum);
    }
    return totalCount;
}`,
    },
  },
  {
    id: 'pat-hash-map-set',
    family: 'linear',
    title: 'Hash Map / Set',
    trigger: 'repeated lookup, complement pairs, counts, first-unique, anagram check',
    state: 'map = needed_value → first_index, or value → count; set = seen values',
    watch: 'insert complement before or after current? check before inserting to avoid self-pair',
    skeletons: {
      python: `def hash_map_template(items, target):
    value_to_index = {}   # or defaultdict(int) for counts
    for current_index, current_value in enumerate(items):
        needed = target - current_value          # complement
        if needed in value_to_index:
            return (value_to_index[needed], current_index)
        value_to_index[current_value] = current_index  # insert after check
    return None`,
      javascript: `function hashMapTemplate(items, target) {
  const valueToIndex = new Map();
  for (let currentIndex = 0; currentIndex < items.length; currentIndex += 1) {
    const currentValue = items[currentIndex];
    const needed = target - currentValue;
    if (valueToIndex.has(needed)) return [valueToIndex.get(needed), currentIndex];
    valueToIndex.set(currentValue, currentIndex);  // insert after check
  }
  return null;
}`,
      java: `int[] hashMapTemplate(int[] items, int target) {
    Map<Integer, Integer> valueToIndex = new HashMap<>();
    for (int currentIndex = 0; currentIndex < items.length; currentIndex++) {
        int currentValue = items[currentIndex];
        int needed = target - currentValue;
        if (valueToIndex.containsKey(needed))
            return new int[] { valueToIndex.get(needed), currentIndex };
        valueToIndex.put(currentValue, currentIndex);   // insert after check
    }
    return new int[] {};
}`,
    },
  },
  {
    id: 'pat-monotonic-stack',
    family: 'stack-heap',
    title: 'Monotonic Stack',
    trigger: 'next greater/smaller element, histogram area, span, temperatures',
    state: 'pendingIndices holds indices of unresolved elements in monotonic order',
    watch: 'decide increasing vs decreasing direction first; one wrong choice inverts all results',
    skeletons: {
      python: `def monotonic_stack_template(numbers):
    result = [-1] * len(numbers)     # -1 = no answer found yet
    pending_indices = []             # decreasing stack → next greater
    for current_index, current_value in enumerate(numbers):
        while pending_indices and numbers[pending_indices[-1]] < current_value:
            resolved_index = pending_indices.pop()
            result[resolved_index] = current_index   # current resolves resolved
        pending_indices.append(current_index)
    return result`,
      javascript: `function monotonicStackTemplate(numbers) {
  const result = new Array(numbers.length).fill(-1);
  const pendingIndices = [];   // decreasing stack → next greater
  for (let currentIndex = 0; currentIndex < numbers.length; currentIndex += 1) {
    const currentValue = numbers[currentIndex];
    while (pendingIndices.length > 0 && numbers[pendingIndices.at(-1)] < currentValue) {
      const resolvedIndex = pendingIndices.pop();
      result[resolvedIndex] = currentIndex;
    }
    pendingIndices.push(currentIndex);
  }
  return result;
}`,
      java: `int[] monotonicStackTemplate(int[] numbers) {
    int[] result = new int[numbers.length];
    Arrays.fill(result, -1);
    Deque<Integer> pendingIndices = new ArrayDeque<>();  // decreasing → next greater
    for (int currentIndex = 0; currentIndex < numbers.length; currentIndex++) {
        while (!pendingIndices.isEmpty() && numbers[pendingIndices.peek()] < numbers[currentIndex]) {
            int resolvedIndex = pendingIndices.pop();
            result[resolvedIndex] = currentIndex;
        }
        pendingIndices.push(currentIndex);
    }
    return result;
}`,
    },
  },
  {
    id: 'pat-bfs',
    family: 'graph',
    title: 'BFS',
    trigger: 'shortest unweighted path, nearest target cell, minimum steps, level spread',
    state: 'visitedNodes prevents re-enqueue; first dequeue of a node = its shortest distance',
    watch: 'mark nodes visited when enqueuing, not dequeuing — dequeue-marking causes duplicate entries',
    skeletons: {
      python: `from collections import deque

def bfs_template(graph, start_node, target_node):
    visited_nodes = {start_node}
    queue = deque([(start_node, 0)])     # (node, distance)
    while queue:
        current_node, distance = queue.popleft()
        if current_node == target_node:
            return distance
        for neighbor in graph[current_node]:
            if neighbor not in visited_nodes:
                visited_nodes.add(neighbor)  # mark on enqueue
                queue.append((neighbor, distance + 1))
    return -1`,
      javascript: `function bfsTemplate(graph, startNode, targetNode) {
  const visitedNodes = new Set([startNode]);
  const queue = [{ node: startNode, distance: 0 }];
  for (let queueIndex = 0; queueIndex < queue.length; queueIndex += 1) {
    const { node: currentNode, distance } = queue[queueIndex];
    if (currentNode === targetNode) return distance;
    for (const neighbor of graph.get(currentNode) ?? []) {
      if (!visitedNodes.has(neighbor)) {
        visitedNodes.add(neighbor);          // mark on enqueue
        queue.push({ node: neighbor, distance: distance + 1 });
      }
    }
  }
  return -1;
}`,
      java: `int bfsTemplate(Map<Integer, List<Integer>> graph, int startNode, int targetNode) {
    Set<Integer> visitedNodes = new HashSet<>();
    Queue<int[]> queue = new ArrayDeque<>();  // [node, distance]
    visitedNodes.add(startNode);
    queue.offer(new int[] { startNode, 0 });
    while (!queue.isEmpty()) {
        int[] current = queue.poll();
        int currentNode = current[0], distance = current[1];
        if (currentNode == targetNode) return distance;
        for (int neighbor : graph.getOrDefault(currentNode, List.of())) {
            if (visitedNodes.add(neighbor))   // mark on enqueue
                queue.offer(new int[] { neighbor, distance + 1 });
        }
    }
    return -1;
}`,
    },
  },
  {
    id: 'pat-dfs',
    family: 'graph',
    title: 'DFS',
    trigger: 'connected components, all paths, subtree aggregation, cycle detection',
    state: 'visitedNodes tracks explored nodes; recursion/stack represents the current path',
    watch: 'for directed cycle detection, a plain visited set is insufficient — use white/gray/black coloring',
    skeletons: {
      python: `def dfs_template(graph, start_node):
    visited_nodes = set()
    aggregated_result = []

    def visit(current_node):
        if current_node in visited_nodes:
            return
        visited_nodes.add(current_node)
        aggregated_result.append(current_node)   # process node
        for neighbor in graph[current_node]:
            visit(neighbor)

    visit(start_node)
    return aggregated_result`,
      javascript: `function dfsTemplate(graph, startNode) {
  const visitedNodes = new Set();
  const aggregatedResult = [];

  function visit(currentNode) {
    if (visitedNodes.has(currentNode)) return;
    visitedNodes.add(currentNode);
    aggregatedResult.push(currentNode);    // process node
    for (const neighbor of graph.get(currentNode) ?? []) {
      visit(neighbor);
    }
  }

  visit(startNode);
  return aggregatedResult;
}`,
      java: `List<Integer> dfsTemplate(Map<Integer, List<Integer>> graph, int startNode) {
    Set<Integer> visitedNodes = new HashSet<>();
    List<Integer> aggregatedResult = new ArrayList<>();
    dfsVisit(graph, startNode, visitedNodes, aggregatedResult);
    return aggregatedResult;
}

void dfsVisit(Map<Integer, List<Integer>> graph, int currentNode,
              Set<Integer> visitedNodes, List<Integer> aggregatedResult) {
    if (!visitedNodes.add(currentNode)) return;
    aggregatedResult.add(currentNode);    // process node
    for (int neighbor : graph.getOrDefault(currentNode, List.of()))
        dfsVisit(graph, neighbor, visitedNodes, aggregatedResult);
}`,
    },
  },
  {
    id: 'pat-topo-sort',
    family: 'graph',
    title: 'Topological Sort',
    trigger: 'build order, course prerequisites, task dependencies with no cycles',
    state: 'indegreeByNode tracks in-edges; zero-indegree queue holds nodes safe to process',
    watch: 'if processed node count is less than total node count, a cycle exists — signal invalid',
    skeletons: {
      python: `from collections import defaultdict, deque

def topological_sort(num_nodes, edges):
    indegree_by_node = defaultdict(int)
    neighbors_by_node = defaultdict(list)
    for source_node, target_node in edges:
        neighbors_by_node[source_node].append(target_node)
        indegree_by_node[target_node] += 1
    zero_indegree_queue = deque(
        node for node in range(num_nodes) if indegree_by_node[node] == 0
    )
    ordered_nodes = []
    while zero_indegree_queue:
        current_node = zero_indegree_queue.popleft()
        ordered_nodes.append(current_node)
        for neighbor in neighbors_by_node[current_node]:
            indegree_by_node[neighbor] -= 1
            if indegree_by_node[neighbor] == 0:
                zero_indegree_queue.append(neighbor)
    return ordered_nodes if len(ordered_nodes) == num_nodes else []`,
      javascript: `function topologicalSort(numNodes, edges) {
  const indegreeByNode = new Array(numNodes).fill(0);
  const neighborsByNode = Array.from({ length: numNodes }, () => []);
  for (const [sourceNode, targetNode] of edges) {
    neighborsByNode[sourceNode].push(targetNode);
    indegreeByNode[targetNode] += 1;
  }
  const zeroIndegreeQueue = [];
  for (let node = 0; node < numNodes; node += 1) {
    if (indegreeByNode[node] === 0) zeroIndegreeQueue.push(node);
  }
  const orderedNodes = [];
  for (let queueIndex = 0; queueIndex < zeroIndegreeQueue.length; queueIndex += 1) {
    const currentNode = zeroIndegreeQueue[queueIndex];
    orderedNodes.push(currentNode);
    for (const neighbor of neighborsByNode[currentNode]) {
      indegreeByNode[neighbor] -= 1;
      if (indegreeByNode[neighbor] === 0) zeroIndegreeQueue.push(neighbor);
    }
  }
  return orderedNodes.length === numNodes ? orderedNodes : [];
}`,
      java: `List<Integer> topologicalSort(int numNodes, int[][] edges) {
    int[] indegreeByNode = new int[numNodes];
    List<List<Integer>> neighborsByNode = new ArrayList<>();
    for (int i = 0; i < numNodes; i++) neighborsByNode.add(new ArrayList<>());
    for (int[] edge : edges) {
        neighborsByNode.get(edge[0]).add(edge[1]);
        indegreeByNode[edge[1]]++;
    }
    Queue<Integer> zeroIndegreeQueue = new ArrayDeque<>();
    for (int node = 0; node < numNodes; node++)
        if (indegreeByNode[node] == 0) zeroIndegreeQueue.offer(node);
    List<Integer> orderedNodes = new ArrayList<>();
    while (!zeroIndegreeQueue.isEmpty()) {
        int currentNode = zeroIndegreeQueue.poll();
        orderedNodes.add(currentNode);
        for (int neighbor : neighborsByNode.get(currentNode)) {
            if (--indegreeByNode[neighbor] == 0) zeroIndegreeQueue.offer(neighbor);
        }
    }
    return orderedNodes.size() == numNodes ? orderedNodes : List.of();
}`,
    },
  },
  {
    id: 'pat-union-find',
    family: 'graph',
    title: 'Union Find',
    trigger: 'dynamic connectivity, number of islands, redundant edge, connected components',
    state: 'parentByItem and sizeByRoot; find() path-compresses; union() merges smaller root into larger',
    watch: 'without path compression and union-by-rank, find() degrades to O(n) per call',
    skeletons: {
      python: `class UnionFindTemplate:
    def __init__(self, num_nodes):
        self.parent = list(range(num_nodes))
        self.size = [1] * num_nodes

    def find(self, node):
        if self.parent[node] != node:
            self.parent[node] = self.find(self.parent[node])  # path compress
        return self.parent[node]

    def union(self, node_a, node_b):
        root_a, root_b = self.find(node_a), self.find(node_b)
        if root_a == root_b:
            return False           # already connected
        if self.size[root_a] < self.size[root_b]:
            root_a, root_b = root_b, root_a
        self.parent[root_b] = root_a
        self.size[root_a] += self.size[root_b]
        return True`,
      javascript: `class UnionFindTemplate {
  constructor(numNodes) {
    this.parent = Array.from({ length: numNodes }, (_, i) => i);
    this.size = new Array(numNodes).fill(1);
  }

  find(node) {
    if (this.parent[node] !== node)
      this.parent[node] = this.find(this.parent[node]);  // path compress
    return this.parent[node];
  }

  union(nodeA, nodeB) {
    let rootA = this.find(nodeA);
    let rootB = this.find(nodeB);
    if (rootA === rootB) return false;   // already connected
    if (this.size[rootA] < this.size[rootB]) [rootA, rootB] = [rootB, rootA];
    this.parent[rootB] = rootA;
    this.size[rootA] += this.size[rootB];
    return true;
  }
}`,
      java: `class UnionFindTemplate {
    private final int[] parent;
    private final int[] size;

    UnionFindTemplate(int numNodes) {
        parent = new int[numNodes];
        size = new int[numNodes];
        for (int i = 0; i < numNodes; i++) { parent[i] = i; size[i] = 1; }
    }

    int find(int node) {
        if (parent[node] != node) parent[node] = find(parent[node]);
        return parent[node];
    }

    boolean union(int nodeA, int nodeB) {
        int rootA = find(nodeA), rootB = find(nodeB);
        if (rootA == rootB) return false;
        if (size[rootA] < size[rootB]) { int tmp = rootA; rootA = rootB; rootB = tmp; }
        parent[rootB] = rootA;
        size[rootA] += size[rootB];
        return true;
    }
}`,
    },
  },
  {
    id: 'pat-heap-top-k',
    family: 'stack-heap',
    title: 'Heap — Top K',
    trigger: 'top k largest/smallest elements, k-th element, merge k sorted streams',
    state: 'min-heap of size ≤ k; heap top is the weakest of the k best seen so far',
    watch: 'comparator direction controls largest-k vs smallest-k — verify with a small example first',
    skeletons: {
      python: `import heapq

def top_k_largest(numbers, k):
    min_heap = []                       # min-heap keeps top-k largest
    for current_number in numbers:
        heapq.heappush(min_heap, current_number)
        if len(min_heap) > k:
            heapq.heappop(min_heap)     # evict the smallest seen so far
    return list(min_heap)               # all k elements; min_heap[0] is k-th largest`,
      javascript: `// JS has no built-in heap; assume MinHeap class from code kit
function topKLargest(numbers, k) {
  const minHeap = new MinHeap((a, b) => a < b);   // min at top
  for (const currentNumber of numbers) {
    minHeap.push(currentNumber);
    if (minHeap.values.length > k) minHeap.pop(); // evict weakest
  }
  return minHeap.values;   // heap top is the k-th largest
}`,
      java: `List<Integer> topKLargest(int[] numbers, int k) {
    PriorityQueue<Integer> minHeap = new PriorityQueue<>(); // natural order = min at top
    for (int currentNumber : numbers) {
        minHeap.offer(currentNumber);
        if (minHeap.size() > k) minHeap.poll();   // evict smallest
    }
    return new ArrayList<>(minHeap);
}`,
    },
  },
  {
    id: 'pat-heap-two-heaps',
    family: 'stack-heap',
    title: 'Heap — Two Heaps (running median)',
    trigger: 'running median, sliding median, balanced lower/upper partition',
    state: 'maxHeap holds lower half; minHeap holds upper half; sizes differ by at most 1',
    watch: 'after every insert, re-check both the order invariant and the size-balance invariant',
    skeletons: {
      python: `import heapq

class RunningMedian:
    def __init__(self):
        self.lower_max_heap = []   # max-heap via negation
        self.upper_min_heap = []   # min-heap

    def add(self, value):
        heapq.heappush(self.lower_max_heap, -value)
        # order invariant: lower top <= upper top
        if self.upper_min_heap and -self.lower_max_heap[0] > self.upper_min_heap[0]:
            heapq.heappush(self.upper_min_heap, -heapq.heappop(self.lower_max_heap))
        # size invariant: sizes differ by at most 1
        if len(self.lower_max_heap) > len(self.upper_min_heap) + 1:
            heapq.heappush(self.upper_min_heap, -heapq.heappop(self.lower_max_heap))
        elif len(self.upper_min_heap) > len(self.lower_max_heap):
            heapq.heappush(self.lower_max_heap, -heapq.heappop(self.upper_min_heap))

    def median(self):
        if len(self.lower_max_heap) > len(self.upper_min_heap):
            return -self.lower_max_heap[0]
        return (-self.lower_max_heap[0] + self.upper_min_heap[0]) / 2`,
      javascript: `// Assumes MinHeap from code kit; MaxHeap = MinHeap with reversed comparator
class RunningMedian {
  constructor() {
    this.lowerMaxHeap = new MinHeap((a, b) => a > b);  // max at top
    this.upperMinHeap = new MinHeap((a, b) => a < b);  // min at top
  }

  add(value) {
    this.lowerMaxHeap.push(value);
    // order invariant
    if (this.upperMinHeap.values.length > 0 &&
        this.lowerMaxHeap.values[0] > this.upperMinHeap.values[0]) {
      this.upperMinHeap.push(this.lowerMaxHeap.pop());
    }
    // size invariant
    if (this.lowerMaxHeap.values.length > this.upperMinHeap.values.length + 1)
      this.upperMinHeap.push(this.lowerMaxHeap.pop());
    else if (this.upperMinHeap.values.length > this.lowerMaxHeap.values.length)
      this.lowerMaxHeap.push(this.upperMinHeap.pop());
  }

  median() {
    if (this.lowerMaxHeap.values.length > this.upperMinHeap.values.length)
      return this.lowerMaxHeap.values[0];
    return (this.lowerMaxHeap.values[0] + this.upperMinHeap.values[0]) / 2;
  }
}`,
      java: `class RunningMedian {
    private final PriorityQueue<Integer> lowerMaxHeap =
        new PriorityQueue<>(Comparator.reverseOrder());
    private final PriorityQueue<Integer> upperMinHeap = new PriorityQueue<>();

    void add(int value) {
        lowerMaxHeap.offer(value);
        // order invariant
        if (!upperMinHeap.isEmpty() && lowerMaxHeap.peek() > upperMinHeap.peek())
            upperMinHeap.offer(lowerMaxHeap.poll());
        // size invariant
        if (lowerMaxHeap.size() > upperMinHeap.size() + 1)
            upperMinHeap.offer(lowerMaxHeap.poll());
        else if (upperMinHeap.size() > lowerMaxHeap.size())
            lowerMaxHeap.offer(upperMinHeap.poll());
    }

    double median() {
        if (lowerMaxHeap.size() > upperMinHeap.size()) return lowerMaxHeap.peek();
        return (lowerMaxHeap.peek() + upperMinHeap.peek()) / 2.0;
    }
}`,
    },
  },
  {
    id: 'pat-backtracking',
    family: 'backtracking',
    title: 'Backtracking (subsets / permutations / combinations)',
    trigger: 'all subsets, all permutations, all combinations, constraint-satisfaction',
    state: 'currentPath holds the partial choice; startIndex or usedFlags tracks available items',
    watch: 'duplicates: sort first, then skip nums[i] when i > startIndex and nums[i] == nums[i-1]',
    skeletons: {
      python: `def backtrack_template(candidates, target, start_index=0,
                          current_path=None, all_results=None):
    if current_path is None: current_path = []
    if all_results is None:  all_results = []
    if is_complete(current_path, target):   # base case: record solution
        all_results.append(list(current_path))
        return
    for choice_index in range(start_index, len(candidates)):
        # skip duplicates after sorting
        if choice_index > start_index and candidates[choice_index] == candidates[choice_index - 1]:
            continue
        current_path.append(candidates[choice_index])           # choose
        backtrack_template(candidates, target, choice_index + 1,
                           current_path, all_results)           # explore
        current_path.pop()                                      # unchoose
    return all_results`,
      javascript: `function backtrackTemplate(candidates, target) {
  const allResults = [];

  function explore(startIndex, currentPath, remainingTarget) {
    if (remainingTarget === 0) {          // base case
      allResults.push([...currentPath]);
      return;
    }
    for (let choiceIndex = startIndex; choiceIndex < candidates.length; choiceIndex += 1) {
      if (choiceIndex > startIndex && candidates[choiceIndex] === candidates[choiceIndex - 1])
        continue;                        // skip duplicates
      currentPath.push(candidates[choiceIndex]);              // choose
      explore(choiceIndex + 1, currentPath,
              remainingTarget - candidates[choiceIndex]);     // explore
      currentPath.pop();                                      // unchoose
    }
  }

  candidates.sort((a, b) => a - b);
  explore(0, [], target);
  return allResults;
}`,
      java: `List<List<Integer>> backtrackTemplate(int[] candidates, int target) {
    Arrays.sort(candidates);
    List<List<Integer>> allResults = new ArrayList<>();
    explore(candidates, target, 0, new ArrayList<>(), allResults);
    return allResults;
}

void explore(int[] candidates, int remainingTarget, int startIndex,
             List<Integer> currentPath, List<List<Integer>> allResults) {
    if (remainingTarget == 0) {
        allResults.add(new ArrayList<>(currentPath)); return;
    }
    for (int choiceIndex = startIndex; choiceIndex < candidates.length; choiceIndex++) {
        if (choiceIndex > startIndex && candidates[choiceIndex] == candidates[choiceIndex - 1])
            continue;                    // skip duplicates
        currentPath.add(candidates[choiceIndex]);              // choose
        explore(candidates, remainingTarget - candidates[choiceIndex],
                choiceIndex + 1, currentPath, allResults);    // explore
        currentPath.remove(currentPath.size() - 1);           // unchoose
    }
}`,
    },
  },
  {
    id: 'pat-1d-dp',
    family: 'dp',
    title: '1D DP',
    trigger: 'count/min/max over choices on a 1D sequence — stairs, coins, LIS, house robber',
    state: 'dp[i] = best answer for prefix ending at index i; built left to right from base cases',
    watch: 'set all base cases before the main loop; a missing base case causes silent wrong answers',
    skeletons: {
      python: `def dp_1d_template(values):
    n = len(values)
    dp = [0] * (n + 1)
    dp[0] = 0   # base case: empty prefix answer
    dp[1] = values[0] if n >= 1 else 0
    for i in range(2, n + 1):
        # transition: best of one step back or two steps back (adapt per problem)
        dp[i] = max(dp[i - 1], dp[i - 2] + values[i - 1])
    return dp[n]`,
      javascript: `function dp1dTemplate(values) {
  const n = values.length;
  const dp = new Array(n + 1).fill(0);
  dp[0] = 0;
  dp[1] = n >= 1 ? values[0] : 0;
  for (let i = 2; i <= n; i += 1) {
    // transition: adapt this line to the specific recurrence
    dp[i] = Math.max(dp[i - 1], dp[i - 2] + values[i - 1]);
  }
  return dp[n];
}`,
      java: `int dp1dTemplate(int[] values) {
    int n = values.length;
    int[] dp = new int[n + 1];
    dp[0] = 0;
    if (n >= 1) dp[1] = values[0];
    for (int i = 2; i <= n; i++) {
        // transition: adapt this line to the specific recurrence
        dp[i] = Math.max(dp[i - 1], dp[i - 2] + values[i - 1]);
    }
    return dp[n];
}`,
    },
  },
  {
    id: 'pat-2d-dp',
    family: 'dp',
    title: '2D DP / Interval DP',
    trigger: 'grid paths, edit distance, longest common subsequence, burst balloons',
    state: 'dp[i][j] = best answer using first i of sequence A and first j of sequence B (or interval i..j)',
    watch: 'fill the base row and base column before the nested loops; off-by-one in index shift is the most common bug',
    skeletons: {
      python: `def dp_2d_template(sequence_a, sequence_b):
    rows, cols = len(sequence_a), len(sequence_b)
    dp = [[0] * (cols + 1) for _ in range(rows + 1)]
    # base cases: empty prefix of A or empty prefix of B
    for row in range(rows + 1): dp[row][0] = row   # adapt to problem
    for col in range(cols + 1): dp[0][col] = col
    for row in range(1, rows + 1):
        for col in range(1, cols + 1):
            if sequence_a[row - 1] == sequence_b[col - 1]:
                dp[row][col] = dp[row - 1][col - 1]   # characters match
            else:
                dp[row][col] = 1 + min(dp[row - 1][col],
                                       dp[row][col - 1],
                                       dp[row - 1][col - 1])  # adapt
    return dp[rows][cols]`,
      javascript: `function dp2dTemplate(sequenceA, sequenceB) {
  const rows = sequenceA.length;
  const cols = sequenceB.length;
  const dp = Array.from({ length: rows + 1 }, () => new Array(cols + 1).fill(0));
  for (let row = 0; row <= rows; row += 1) dp[row][0] = row;  // base cases
  for (let col = 0; col <= cols; col += 1) dp[0][col] = col;
  for (let row = 1; row <= rows; row += 1) {
    for (let col = 1; col <= cols; col += 1) {
      if (sequenceA[row - 1] === sequenceB[col - 1]) {
        dp[row][col] = dp[row - 1][col - 1];       // characters match
      } else {
        dp[row][col] = 1 + Math.min(dp[row - 1][col],
                                    dp[row][col - 1],
                                    dp[row - 1][col - 1]);
      }
    }
  }
  return dp[rows][cols];
}`,
      java: `int dp2dTemplate(String sequenceA, String sequenceB) {
    int rows = sequenceA.length(), cols = sequenceB.length();
    int[][] dp = new int[rows + 1][cols + 1];
    for (int row = 0; row <= rows; row++) dp[row][0] = row;  // base cases
    for (int col = 0; col <= cols; col++) dp[0][col] = col;
    for (int row = 1; row <= rows; row++) {
        for (int col = 1; col <= cols; col++) {
            if (sequenceA.charAt(row - 1) == sequenceB.charAt(col - 1))
                dp[row][col] = dp[row - 1][col - 1];
            else
                dp[row][col] = 1 + Math.min(dp[row - 1][col],
                               Math.min(dp[row][col - 1], dp[row - 1][col - 1]));
        }
    }
    return dp[rows][cols];
}`,
    },
  },
  {
    id: 'pat-binary-search-answer',
    family: 'search',
    title: 'Binary Search on the Answer',
    trigger: 'minimize the maximum, maximize the minimum, feasibility with a monotonic predicate',
    state: 'search space is the answer domain [lo, hi]; feasible(mid) shrinks the range each step',
    watch: 'make the predicate strictly monotonic — adding one more to mid must not flip feasibility',
    skeletons: {
      python: `def binary_search_on_answer(items, max_groups):
    def is_feasible(candidate_answer):
        # return True if candidate_answer satisfies the constraint
        group_count, current_total = 1, 0
        for item in items:
            if current_total + item > candidate_answer:
                group_count += 1
                current_total = 0
            current_total += item
        return group_count <= max_groups

    low_bound = max(items)       # smallest possible answer
    high_bound = sum(items)      # largest possible answer
    best_answer = high_bound
    while low_bound <= high_bound:
        mid_candidate = low_bound + (high_bound - low_bound) // 2
        if is_feasible(mid_candidate):
            best_answer = mid_candidate
            high_bound = mid_candidate - 1    # try smaller
        else:
            low_bound = mid_candidate + 1     # too small, grow
    return best_answer`,
      javascript: `function binarySearchOnAnswer(items, maxGroups) {
  function isFeasible(candidateAnswer) {
    let groupCount = 1, currentTotal = 0;
    for (const item of items) {
      if (currentTotal + item > candidateAnswer) {
        groupCount += 1;
        currentTotal = 0;
      }
      currentTotal += item;
    }
    return groupCount <= maxGroups;
  }

  let lowBound = Math.max(...items);
  let highBound = items.reduce((sum, item) => sum + item, 0);
  let bestAnswer = highBound;
  while (lowBound <= highBound) {
    const midCandidate = lowBound + Math.floor((highBound - lowBound) / 2);
    if (isFeasible(midCandidate)) {
      bestAnswer = midCandidate;
      highBound = midCandidate - 1;
    } else {
      lowBound = midCandidate + 1;
    }
  }
  return bestAnswer;
}`,
      java: `int binarySearchOnAnswer(int[] items, int maxGroups) {
    int lowBound = 0, highBound = 0;
    for (int item : items) { lowBound = Math.max(lowBound, item); highBound += item; }
    int bestAnswer = highBound;
    while (lowBound <= highBound) {
        int midCandidate = lowBound + (highBound - lowBound) / 2;
        if (isFeasible(items, midCandidate, maxGroups)) {
            bestAnswer = midCandidate;
            highBound = midCandidate - 1;
        } else {
            lowBound = midCandidate + 1;
        }
    }
    return bestAnswer;
}

boolean isFeasible(int[] items, int candidateAnswer, int maxGroups) {
    int groupCount = 1, currentTotal = 0;
    for (int item : items) {
        if (currentTotal + item > candidateAnswer) { groupCount++; currentTotal = 0; }
        currentTotal += item;
    }
    return groupCount <= maxGroups;
}`,
    },
  },
];

const COMPLEXITY_CELLS: CodingContent['complexity']['compass']['cells'] = (() => {
  type Row = 'n≤20' | 'n≤100' | 'n≤1k' | 'n≤10k' | 'n≤100k' | 'n≤1M' | 'n≤10M';
  type Col = '2ⁿ' | 'n!' | 'n³' | 'n²' | 'n log n' | 'n' | 'log n';
  const rows: Row[] = ['n≤20', 'n≤100', 'n≤1k', 'n≤10k', 'n≤100k', 'n≤1M', 'n≤10M'];
  const cols: Col[] = ['2ⁿ', 'n!', 'n³', 'n²', 'n log n', 'n', 'log n'];

  // status[row][col] derived from real interview rules of thumb
  const status: Record<Row, Record<Col, 'pass' | 'warn' | 'fail'>> = {
    'n≤20':    { '2ⁿ': 'pass', 'n!': 'warn', 'n³': 'pass', 'n²': 'pass', 'n log n': 'pass', 'n': 'pass', 'log n': 'pass' },
    'n≤100':   { '2ⁿ': 'fail', 'n!': 'fail', 'n³': 'pass', 'n²': 'pass', 'n log n': 'pass', 'n': 'pass', 'log n': 'pass' },
    'n≤1k':    { '2ⁿ': 'fail', 'n!': 'fail', 'n³': 'warn', 'n²': 'pass', 'n log n': 'pass', 'n': 'pass', 'log n': 'pass' },
    'n≤10k':   { '2ⁿ': 'fail', 'n!': 'fail', 'n³': 'fail', 'n²': 'warn', 'n log n': 'pass', 'n': 'pass', 'log n': 'pass' },
    'n≤100k':  { '2ⁿ': 'fail', 'n!': 'fail', 'n³': 'fail', 'n²': 'fail', 'n log n': 'pass', 'n': 'pass', 'log n': 'pass' },
    'n≤1M':    { '2ⁿ': 'fail', 'n!': 'fail', 'n³': 'fail', 'n²': 'fail', 'n log n': 'warn', 'n': 'pass', 'log n': 'pass' },
    'n≤10M':   { '2ⁿ': 'fail', 'n!': 'fail', 'n³': 'fail', 'n²': 'fail', 'n log n': 'fail', 'n': 'pass', 'log n': 'pass' },
  };
  const cells: CodingContent['complexity']['compass']['cells'] = [];
  for (const row of rows) for (const col of cols) cells.push({ row, col, status: status[row][col] });
  return cells;
})();

// ─────────────────────────────────────────────────────────────────────────────
// Top-level export — references the consts declared above.
// ─────────────────────────────────────────────────────────────────────────────

export const codingContent: CodingContent = {
  dashboard: {
    title: 'Coding Interview Field Guide',
    description:
      'Study the live coding loop, common patterns, readable implementations, and the proof habits that close a round.',
    roundPhases: [
      { id: 'restate',    label: 'Restate',    say: 'Restate input, output, and one concrete example.', write: 'Sample input → expected output.' },
      { id: 'ask',        label: 'Ask',         say: 'Ask only questions that change code — size, sortedness, duplicates, mutation, ties, empty.', write: 'Bullet the answers next to the example.' },
      { id: 'baseline',   label: 'Baseline',    say: 'Say the brute force baseline and its complexity.', write: 'Brute force complexity in the corner.' },
      { id: 'bottleneck', label: 'Bottleneck',  say: 'Name the repeated work — lookup, range compute, ordering, revisit, overlap.', write: 'Underline the bottleneck phrase.' },
      { id: 'pick-ds',    label: 'Pick DS',     say: 'Choose the data structure and say what it stores.', write: 'DS name + state definition (one line).' },
      { id: 'invariant',  label: 'Invariant',   say: 'State the invariant in one sentence before code.', write: 'Invariant line above the function signature.' },
      { id: 'code',       label: 'Code',        say: 'Talk through code in invariant terms; use descriptive names.', write: 'Code, with names that match the invariant.' },
      { id: 'prove',      label: 'Prove',       say: 'Trace sample + one edge case; close with final complexity.', write: 'Tick marks beside each test case.' },
    ],
    patternRadar: [
      { id: 'sliding-window', name: 'Sliding window',  trigger: 'longest/shortest contiguous range with a condition', topicSlug: 'patterns' },
      { id: 'two-pointers',   name: 'Two pointers',    trigger: 'sorted input with pair/triplet/partition pressure', topicSlug: 'patterns' },
      { id: 'hash-map',       name: 'Hash map',        trigger: 'repeated lookup, complements, counts', topicSlug: 'code-kit' },
      { id: 'hash-set',       name: 'Hash set',        trigger: 'uniqueness, dedupe, visited', topicSlug: 'code-kit' },
      { id: 'binary-search',  name: 'Binary search',   trigger: 'sorted array or monotonic predicate', topicSlug: 'patterns' },
      { id: 'bfs',            name: 'BFS',             trigger: 'shortest unweighted path, level spread', topicSlug: 'code-kit' },
      { id: 'dfs',            name: 'DFS',             trigger: 'components, all paths, tree aggregation', topicSlug: 'code-kit' },
      { id: 'heap',           name: 'Heap',            trigger: 'top k / merge k / running best', topicSlug: 'code-kit' },
      { id: 'monostack',      name: 'Monotonic stack', trigger: 'next greater/smaller, histogram, temperatures', topicSlug: 'patterns' },
      { id: 'prefix-sum',     name: 'Prefix sum',      trigger: 'range totals, subarray-equals-k, immutable queries', topicSlug: 'patterns' },
      { id: '1d-dp',          name: '1D DP',           trigger: 'count/min/max over repeated choices', topicSlug: 'patterns' },
      { id: 'backtracking',   name: 'Backtracking',    trigger: 'all combinations/permutations/subsets', topicSlug: 'patterns' },
    ],
    codeStylePact:
      'Names match the invariant. Helpers reveal intent. The interviewer should follow the code aloud.',
  },

  mentalModel: {
    thesis: 'Name the state. Protect the invariant. Code so the state is obvious.',
    stateExamples: [
      { pattern: 'Sliding Window', state: 'sum of values in [l, r] is the largest valid window ending at r' },
      { pattern: 'BFS',            state: 'visited ∪ frontier; queue order = distance order' },
      { pattern: 'DP',             state: 'dp[i] = best answer using prefix ending at i' },
      { pattern: 'Two Pointers',   state: 'sorted invariant on l/r; moving l increases sum, moving r decreases it' },
      { pattern: 'Heap',           state: 'heap holds best k candidates seen so far; size capped at k' },
    ],
    edgeCases: ['empty', 'singleton', 'duplicate', 'cycle', 'impossible', 'boundary'],
  },

  cheatsheet: {
    preflight: [
      'input/output/example',
      'constraints',
      'baseline',
      'bottleneck',
      'data structure',
      'invariant',
      'complexity target',
    ],
    complexityCeiling: [
      'n ≤ 20 — exp ok with pruning',
      'n ≤ 1k — O(n²) ceiling',
      'n ≤ 100k — target O(n log n) or O(n)',
      'n ≥ 1M — target O(n) or streaming',
    ],
    patternMatrix: CHEATSHEET_PATTERN_MATRIX_PARTIAL,
  },

  codeKit: { shelves: CODE_KIT_SHELVES_PARTIAL },
  patterns: { entries: PATTERN_ENTRIES_PARTIAL },

  complexity: {
    compass: {
      rows: ['n≤20', 'n≤100', 'n≤1k', 'n≤10k', 'n≤100k', 'n≤1M', 'n≤10M'],
      cols: ['2ⁿ', 'n!', 'n³', 'n²', 'n log n', 'n', 'log n'],
      cells: COMPLEXITY_CELLS,
    },
    constraintTargets: [
      { inputBand: 'n ≤ 20',     target: 'exponential is acceptable if pruning is clear', naturalPatterns: ['backtracking', 'bitmask DP', 'meet in the middle'] },
      { inputBand: 'n ≤ 100',    target: 'O(n³) is often the ceiling',                    naturalPatterns: ['Floyd–Warshall', '3-loop DP'] },
      { inputBand: 'n ≤ 1k',     target: 'O(n²) is often the ceiling',                    naturalPatterns: ['2D DP', 'pair search', 'edit distance'] },
      { inputBand: 'n ≤ 10k',    target: 'O(n² / log n) borderline; O(n √n) ok',          naturalPatterns: ["Mo's algorithm", 'sqrt decomposition'] },
      { inputBand: 'n ≤ 100k',   target: 'O(n log n) or O(n)',                            naturalPatterns: ['heap', 'sort + sweep', 'hash map', 'two-pass', 'prefix sum'] },
      { inputBand: 'n ≤ 1M',     target: 'O(n) only — avoid log factors when possible',   naturalPatterns: ['counting sort', 'streaming aggregation', 'union find'] },
      { inputBand: 'n ≤ 10M',    target: 'streaming O(n) or O(log n)',                    naturalPatterns: ['hash counting', 'reservoir sample', 'incremental aggregation'] },
    ],
    proofLanguage: [
      'each item enters and leaves once',
      'each edge is visited at most twice',
      'heap size never exceeds k',
      'each memo state is solved once',
      'binary search shrinks the search range every iteration',
    ],
    costReference: [
      { op: 'hash map insert / lookup', cost: 'O(1) average' },
      { op: 'heap push / pop',          cost: 'O(log n)' },
      { op: 'sort',                     cost: 'O(n log n)' },
      { op: 'BFS / DFS',                cost: 'O(V + E)' },
      { op: 'set membership',           cost: 'O(1) average' },
      { op: 'union find with rank + path compression', cost: 'O(α(n)) ≈ O(1)' },
    ],
  },
};
