"""Reviewed teaching material. These finite checks do not prove correctness."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Case:
    id: str
    title: str
    purpose: str
    script: str  # Trusted harness code; the model can select IDs, never write this.
    expected: object


@dataclass(frozen=True)
class TransferReflection:
    transfer_snippet: str
    transfer_prompt: str
    transfer_choices: tuple
    correct_choice_index: int
    explanation: str

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __contains__(self, key):
        return hasattr(self, key)

    def keys(self):
        return ("transfer_snippet", "transfer_prompt", "transfer_choices", "correct_choice_index", "explanation")

    def values(self):
        return tuple(getattr(self, k) for k in self.keys())

    def items(self):
        return tuple((k, getattr(self, k)) for k in self.keys())


@dataclass(frozen=True)
class Exercise:
    id: str
    title: str
    concept: str
    spec: str
    starter: str
    entrypoint: str
    prediction_code: str
    choices: tuple
    prediction: Case
    cases: tuple
    solution: str
    explanation: str
    hints: tuple
    forbidden: tuple = ()
    reflection: TransferReflection = None

    def case(self, case_id):
        return next(c for c in (self.prediction, *self.cases) if c.id == case_id)


BASKET = Exercise(
    id="basket", title="The basket that remembers", concept="Shared mutable state",
    spec=("add_item adds an item to a basket. When no basket is supplied (or it is None), "
          "each call must create a fresh list. A supplied list, including an empty one, "
          "must be modified and returned as the same object. Items are strings."),
    starter="def add_item(item, items=[]):\n    items.append(item)\n    return items\n",
    entrypoint="add_item",
    prediction_code='print(add_item("apple"))\nprint(add_item("banana"))',
    choices=('["banana"]', '["apple", "banana"]', '[]', "I'm not sure"),
    prediction=Case("prediction", "Second independent call", "Observe the second printed value",
                    'fn("apple")\nactual = list(fn("banana"))', ["banana"]),
    cases=(
        Case("fresh_repeat", "Independent calls", "Two omitted baskets must be separate lists",
             'a = fn("apple")\nfirst = list(a)\nb = fn("banana")\n'
             'actual = {"first": first, "second": list(b), "same_object": a is b}',
             {"first": ["apple"], "second": ["banana"], "same_object": False}),
        Case("provided_empty", "Caller supplies an empty basket", "Preserve the caller's empty list",
             'basket = []\nout = fn("pear", basket)\n'
             'actual = {"returned": out, "basket": basket, "same_object": out is basket}',
             {"returned": ["pear"], "basket": ["pear"], "same_object": True}),
        Case("provided_nonempty", "Caller supplies a filled basket", "Modify and return the supplied list",
             'basket = ["kiwi"]\nout = fn("pear", basket)\n'
             'actual = {"returned": out, "basket": basket, "same_object": out is basket}',
             {"returned": ["kiwi", "pear"], "basket": ["kiwi", "pear"], "same_object": True}),
        Case("explicit_none", "Explicit None", "None also means a fresh basket",
             'actual = fn("plum", None)', ["plum"]),
        Case("later_mutation", "Mutate an earlier basket", "Later baskets must not inherit earlier mutations",
             'a = fn("apple")\na.append("kiwi")\nactual = fn("banana")', ["banana"]),
    ),
    solution="def add_item(item, items=None):\n    if items is None:\n        items = []\n    items.append(item)\n    return items\n",
    explanation=("A default list is created when the function is defined and reused across omitted "
                 "arguments. None can represent an omitted basket. Checking identity with None "
                 "preserves an explicitly supplied empty list; a truthiness check would replace it."),
    hints=("Which part of the second output came from the earlier call?",
           "When is a function's default value created, and how long can that object survive?",
           "How does your condition distinguish a missing basket from a supplied empty basket?"),
    reflection=TransferReflection(
        transfer_snippet="first = [1]\nsecond = first\nsecond.append(2)\nprint(first)",
        transfer_prompt="What will this code print?",
        transfer_choices=("[1]", "[1, 2]", "[2]", "Error"),
        correct_choice_index=1,
        explanation=("Both 'first' and 'second' refer to the exact same list in memory. "
                     "Mutating the list via 'second' directly affects 'first', just as a default "
                     "mutable argument is shared across independent function calls."),
    ),
)

LARGEST = Exercise(
    id="largest", title="The largest number that isn't there", concept="Initialization and input coverage",
    spec="largest returns the greatest integer in a list. An empty list must raise ValueError.",
    starter="def largest(numbers):\n    best = 0\n    for number in numbers:\n        if number > best:\n            best = number\n    return best\n",
    entrypoint="largest", prediction_code="print(largest([-8, -3, -11]))",
    choices=("-3", "0", "-11", "I'm not sure"),
    prediction=Case("prediction", "All-negative input", "Observe the returned value",
                    "actual = fn([-8, -3, -11])", -3),
    cases=(
        Case("positive", "Positive values", "Basic comparison", "actual = fn([2, 9, 4])", 9),
        Case("negative", "All-negative values", "The result must come from the input", "actual = fn([-8, -3, -11])", -3),
        Case("single", "One negative value", "One-element boundary", "actual = fn([-7])", -7),
        Case("empty", "Empty input", "Required error behavior",
             'try:\n    actual = {"returned": fn([])}\nexcept ValueError:\n    actual = {"error": "ValueError"}',
             {"error": "ValueError"}),
        Case("mixed", "Mixed values and duplicates", "Ordinary mixed input", "actual = fn([-4, 0, 6, 6, 2])", 6),
    ),
    solution="def largest(numbers):\n    if not numbers:\n        raise ValueError('An empty list has no largest value')\n    best = numbers[0]\n    for number in numbers[1:]:\n        if number > best:\n            best = number\n    return best\n",
    explanation="An initial candidate must be justified by the input. Handle the empty case explicitly before choosing an element.",
    hints=("Is the returned value present in the input?", "What assumption is made by the initial candidate?",
           "Consider the initial candidate and the separate empty-input requirement."),
    reflection=TransferReflection(
        transfer_snippet=("def find_minimum(numbers):\n"
                          "    lowest = 100\n"
                          "    for n in numbers:\n"
                          "        if n < lowest:\n"
                          "            lowest = n\n"
                          "    return lowest\n\n"
                          "print(find_minimum([120, 150, 200]))"),
        transfer_prompt="What does find_minimum([120, 150, 200]) return?",
        transfer_choices=("120", "100", "150", "ValueError"),
        correct_choice_index=1,
        explanation=("Because 'lowest' was arbitrarily initialized to 100, if all numbers in the input "
                     "exceed 100, the function returns 100 even though 100 was not in the input. "
                     "An initial candidate must be drawn directly from the input data (e.g. numbers[0])."),
    ),
)

TOTAL = Exercise(
    id="total", title="The disappearing last number", concept="Exclusive loop boundaries",
    spec="total returns the sum of every integer in a list. It returns zero for an empty list.",
    starter="def total(numbers):\n    result = 0\n    for i in range(len(numbers) - 1):\n        result += numbers[i]\n    return result\n",
    entrypoint="total", prediction_code="print(total([2, 3, 4]))",
    choices=("9", "5", "4", "I'm not sure"),
    prediction=Case("prediction", "Three integers", "Observe the returned total", "actual = fn([2, 3, 4])", 9),
    cases=(
        Case("ordinary", "Three integers", "Include every position", "actual = fn([2, 3, 4])", 9),
        Case("single", "One integer", "Smallest nonempty list", "actual = fn([7])", 7),
        Case("empty", "Empty input", "Defined empty sum", "actual = fn([])", 0),
        Case("negative", "Negative integers", "Signed values", "actual = fn([-2, -3])", -5),
        Case("ending_zero", "Last element is zero", "A value can conceal a missing position", "actual = fn([2, 3, 0])", 5),
    ),
    solution="def total(numbers):\n    result = 0\n    for number in numbers:\n        result += number\n    return result\n",
    explanation="The original range stops before the final valid index. Iterating directly over values includes every element.",
    hints=("Which input values contributed to the observed total?", "Which indices does this range actually produce?",
           "Compare the last index the loop visits with the last valid index of the list."),
    reflection=TransferReflection(
        transfer_snippet=("chars = ['a', 'b', 'c', 'd']\n"
                          "result = ''\n"
                          "for i in range(len(chars) - 1):\n"
                          "    result += chars[i]\n"
                          "print(result)"),
        transfer_prompt="What will this code print?",
        transfer_choices=("abcd", "abc", "bcd", "ab"),
        correct_choice_index=1,
        explanation=("range(len(chars) - 1) produces indices 0, 1, and 2, completely omitting index 3 ('d'). "
                     "In Python, range(stop) is exclusive of stop, so range(n - 1) iterates n - 1 times, "
                     "stopping before the final element just as in the total exercise."),
    ),
)

CLOSURES = Exercise(
    id="closures", title="The functions that forgot their numbers", concept="Late binding in closures",
    spec=("make_multipliers returns a list of n functions where the k-th function multiplies its "
          "argument by k: funcs[k](x) == x * k for 0 <= k < n. For n <= 0, it returns an empty list."),
    starter=("def make_multipliers(n):\n"
             "    funcs = []\n"
             "    for i in range(n):\n"
             "        funcs.append(lambda x: x * i)\n"
             "    return funcs\n"),
    entrypoint="make_multipliers",
    prediction_code="funcs = make_multipliers(3)\nprint([f(10) for f in funcs])",
    choices=("[0, 10, 20]", "[20, 20, 20]", "[0, 0, 0]", "I'm not sure"),
    prediction=Case("prediction", "Three multipliers called with 10",
                    "Observe that all returned functions share the final loop variable",
                    "funcs = fn(3)\nactual = [f(10) for f in funcs]", [0, 10, 20]),
    cases=(
        Case("three_functions", "Three functions with varied inputs", "Verify each index multiplies by its position",
             "funcs = fn(3)\nactual = [funcs[0](5), funcs[1](5), funcs[2](5)]", [0, 5, 10]),
        Case("single_function", "Single function (n=1)", "Boundary check for n=1",
             "funcs = fn(1)\nactual = [funcs[0](7)]", [0]),
        Case("empty", "Zero functions (n=0)", "Empty list when n is 0",
             "actual = fn(0)", []),
        Case("negative_n", "Negative n (n=-2)", "Empty list for negative n",
             "actual = fn(-2)", []),
        Case("trap_repeated_calls", "Four functions with varied inputs", "Independent calls with different arguments",
             "funcs = fn(4)\nactual = [funcs[3](2), funcs[2](3), funcs[1](10), funcs[0](99)]", [6, 6, 10, 0]),
    ),
    solution=("def make_multipliers(n):\n"
              "    funcs = []\n"
              "    for i in range(n):\n"
              "        funcs.append(lambda x, i=i: x * i)\n"
              "    return funcs\n"),
    explanation=("Python closures look up variables by name when the function is called, not when it is defined. "
                 "By the time any multiplier runs, 'i' equals n - 1. Binding 'i=i' as a default argument captures "
                 "the current loop value at definition time."),
    hints=("When does the multiplication actually occur: when make_multipliers runs, or when the returned function is called?",
           "What is the value of 'i' in the surrounding scope after the loop completes?",
           "How could each returned function retain the loop value that belonged to its own iteration?"),
    forbidden=(r"\bi\s*=\s*i\b", r"\bdefault\s+(argument|parameter)", r"\blate\s+binding\b"),
    reflection=TransferReflection(
        transfer_snippet=("actions = []\n"
                          "for word in ['hello', 'world']:\n"
                          "    actions.append(lambda: word)\n\n"
                          "print([act() for act in actions])"),
        transfer_prompt="What will [act() for act in actions] evaluate to?",
        transfer_choices=("['hello', 'world']", "['world', 'world']", "['hello', 'hello']", "Error"),
        correct_choice_index=1,
        explanation=("In Python, closures bind variables by name, not value. When the lambdas are executed, "
                     "the loop has finished and 'word' refers to its final bound value 'world'. "
                     "To capture the current value at definition time, bind it as a default parameter (lambda w=word: w)."),
    ),
)

COUNTDOWN = Exercise(
    id="countdown", title="The countdown that stops too soon", concept="Recursion base cases and boundary conditions",
    spec=("countdown returns a list of integers counting down from n to 0 inclusive. "
          "For negative n, it must return an empty list."),
    starter=("def countdown(n):\n"
             "    if n <= 1:\n"
             "        return [1]\n"
             "    return [n] + countdown(n - 1)\n"),
    entrypoint="countdown",
    prediction_code="print(countdown(3))",
    choices=("[3, 2, 1, 0]", "[3, 2, 1]", "[1]", "I'm not sure"),
    prediction=Case("prediction", "Countdown from 3", "Observe where the recursive descent stops",
                    "actual = fn(3)", [3, 2, 1, 0]),
    cases=(
        Case("positive", "Countdown from 4", "Normal recursion down to 0",
             "actual = fn(4)", [4, 3, 2, 1, 0]),
        Case("zero", "Countdown from 0", "Zero boundary must include 0",
             "actual = fn(0)", [0]),
        Case("single", "Countdown from 1", "Countdown from 1 must include 1 and 0",
             "actual = fn(1)", [1, 0]),
        Case("negative", "Negative input (n=-3)", "Negative inputs must return an empty list",
             "actual = fn(-3)", []),
        Case("trap_large", "Countdown from 10", "Larger input verifying full chain down to 0",
             "actual = fn(10)", [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]),
    ),
    solution=("def countdown(n):\n"
              "    if n < 0:\n"
              "        return []\n"
              "    if n == 0:\n"
              "        return [0]\n"
              "    return [n] + countdown(n - 1)\n"),
    explanation=("The base case n <= 1 stopped the countdown at 1 instead of reaching 0, and incorrectly returned [1] "
                 "for zero and negative inputs. Separating negative inputs (empty list) and the zero base case ([0]) "
                 "correctly terminates the recursive descent."),
    hints=("Which values are present in the observed output, and which required stopping value is missing?",
           "What does the starter code return when called with 0 or a negative number?",
           "How can you separate the negative input guard from the zero base case?"),
    forbidden=(r"\bn\s*<\s*0\b", r"\bn\s*==\s*0\b", r"\breturn\s*\[0\]"),
    reflection=TransferReflection(
        transfer_snippet=("def count_down_strings(n):\n"
                          "    if n == 1:\n"
                          "        return ['blastoff!']\n"
                          "    return [str(n)] + count_down_strings(n - 1)\n\n"
                          "print(count_down_strings(3))"),
        transfer_prompt="What will count_down_strings(3) return?",
        transfer_choices=("['3', '2', '1', 'blastoff!']", "['3', '2', 'blastoff!']", "['3', 'blastoff!']", "['blastoff!']"),
        correct_choice_index=1,
        explanation=("The base case terminates at n == 1 without prepending '1' to the resulting list, "
                     "omitting 1 from the countdown descent. The recursion must continue down to 0 before "
                     "returning the terminal marker, just like the countdown exercise omitted 0."),
    ),
)

SHALLOW_COPY = Exercise(
    id="shallow_copy", title="The copy that wasn't independent",
    concept="Shallow vs. deep copies with nested structures",
    spec=("clone_grid creates an independent copy of a 2D list of numbers or characters. "
          "Modifying any cell or sublist in the returned copy must not modify the original grid. "
          "An empty input list returns an empty list."),
    starter=("def clone_grid(grid):\n"
             "    return list(grid)\n"),
    entrypoint="clone_grid",
    prediction_code=("original = [['A', 'B'], ['C', 'D']]\n"
                     "copy = clone_grid(original)\n"
                     "copy[0][0] = 'Z'\n"
                     "print(original[0][0])"),
    choices=("A", "Z", "Error", "I'm not sure"),
    prediction=Case("prediction", "Mutate copied grid cell",
                    "Observe that original grid was modified by modifying the copy",
                    "grid = [['A', 'B'], ['C', 'D']]\ndupe = fn(grid)\ndupe[0][0] = 'Z'\nactual = grid[0][0]", "A"),
    cases=(
        Case("separate_cells", "Modify first row cell", "Changing duplicate cell leaves original intact",
             'g = [["X", "O"], ["O", "X"]]\nc = fn(g)\nc[0][1] = "X"\n'
             'actual = {"orig_cell": g[0][1], "copy_cell": c[0][1], "different": g[0][1] != c[0][1]}',
             {"orig_cell": "O", "copy_cell": "X", "different": True}),
        Case("append_to_row", "Append element to row", "Row in copy grows independently without affecting original",
             'g = [[1, 2], [3, 4]]\nc = fn(g)\nc[1].append(5)\n'
             'actual = {"orig_len": len(g[1]), "copy_len": len(c[1])}',
             {"orig_len": 2, "copy_len": 3}),
        Case("empty_grid", "Empty grid input", "Empty list input must return a new empty list",
             'actual = fn([])', []),
        Case("single_row", "Single-row grid", "One row boundary must be independently copied",
             'g = [["solo"]]\nc = fn(g)\nc[0][0] = "changed"\n'
             'actual = {"original": g[0][0], "copy": c[0][0]}',
             {"original": "solo", "copy": "changed"}),
        Case("separate_instances", "Identity check across rows", "Each row in the copy must be a distinct object in memory",
             'g = [[10, 20], [30, 40], [50, 60]]\nc = fn(g)\n'
             'actual = [c[i] is not g[i] for i in range(len(g))]',
             [True, True, True]),
    ),
    solution=("def clone_grid(grid):\n"
              "    return [list(row) for row in grid]\n"),
    explanation=("A shallow copy such as list(grid) or grid.copy() creates a new outer list, but every "
                 "inner row is still a shared reference to the same list in memory. To make an independent "
                 "grid, copy each inner row individually (e.g. using a list comprehension: [list(row) for row in grid])."),
    hints=("Notice which grid was printed: original[0][0]. Why did modifying the copy affect the original?",
           "What does list(grid) do to the inner elements? Are the row lists new objects, or the same objects?",
           "How can you ensure that each row inside the grid is also newly copied when building the new outer list?"),
    forbidden=(r"\bdeepcopy\b", r"\[\s*list\(row\)\s+for\s+row\s+in\s+grid\s*\]"),
    reflection=TransferReflection(
        transfer_snippet=("person = {'name': 'Ada', 'hobbies': ['reading']}\n"
                          "clone = person.copy()\n"
                          "clone['hobbies'].append('coding')\n"
                          "print(person['hobbies'])"),
        transfer_prompt="What will print(person['hobbies']) display?",
        transfer_choices=("['reading']", "['reading', 'coding']", "['coding']", "Error"),
        correct_choice_index=1,
        explanation=("Dictionary .copy() creates a shallow copy. The outer dict is new, but the nested 'hobbies' "
                     "list is shared by both dictionaries. Appending via clone['hobbies'] mutates the list "
                     "referenced by person['hobbies'], just like rows in a shallow-copied 2D grid."),
    ),
)

SCOPE_LEAK = Exercise(
    id="scope_leak", title="The variable found too late",
    concept="Enclosing variable scope and UnboundLocalError",
    spec=("make_counter creates and returns an incrementer function tick(step=1). "
          "Starting from start (default 0), each call to tick increments the count by step "
          "and returns the new cumulative count. Independent counters must maintain independent counts."),
    starter=("def make_counter(start=0):\n"
             "    count = start\n"
             "    def tick(step=1):\n"
             "        count += step\n"
             "        return count\n"
             "    return tick\n"),
    entrypoint="make_counter",
    prediction_code=("c = make_counter(0)\n"
                     "try:\n"
                     "    print(c())\n"
                     "except UnboundLocalError:\n"
                     "    print('UnboundLocalError')"),
    choices=("1", "0", "UnboundLocalError", "I'm not sure"),
    prediction=Case("prediction", "First call to counter",
                    "Observe that assigning without nonlocal triggers UnboundLocalError",
                    'c = fn(0)\n'
                    'try:\n'
                    '    actual = c()\n'
                    'except UnboundLocalError:\n'
                    '    actual = "UnboundLocalError"', 1),
    cases=(
        Case("consecutive_calls", "Three sequential increments", "Count increments by 1 on each call",
             'c = fn(0)\nactual = [c(), c(), c()]', [1, 2, 3]),
        Case("custom_step", "Custom step increments", "Count increments by custom step parameter",
             'c = fn(10)\nactual = [c(5), c(10)]', [15, 25]),
        Case("negative_steps", "Negative step decrements", "Count decrements when step is negative",
             'c = fn(5)\nactual = [c(-2), c(-3)]', [3, 0]),
        Case("independent_instances", "Two separate counters", "Modifying counter A does not modify counter B",
             'a = fn(0)\nb = fn(100)\na()\na()\nactual = {"a": a(), "b": b()}', {"a": 3, "b": 101}),
        Case("default_start", "Default start parameter", "Omitting start begins from 0",
             'c = fn()\nactual = c(4)', 4),
    ),
    solution=("def make_counter(start=0):\n"
              "    count = start\n"
              "    def tick(step=1):\n"
              "        nonlocal count\n"
              "        count += step\n"
              "        return count\n"
              "    return tick\n"),
    explanation=("In Python, assigning to a variable (including count += step) inside a function causes "
                 "Python to treat it as local to that function. Because count is read before it has been "
                 "locally assigned, Python raises UnboundLocalError. Declaring 'nonlocal count' tells Python "
                 "to rebind the variable in the enclosing make_counter scope."),
    hints=("Why did Python report an UnboundLocalError when 'count' is clearly initialized in make_counter?",
           "When Python sees 'count += step' inside tick(), does it treat 'count' as a local variable or as an outer variable?",
           "Which Python keyword informs the inner function that an assigned variable belongs to the enclosing function's scope?"),
    forbidden=(r"\bnonlocal\b", r"count\s*\[0\]"),
    reflection=TransferReflection(
        transfer_snippet=("score = 10\n"
                          "def boost():\n"
                          "    score += 5\n"
                          "    return score\n\n"
                          "try:\n"
                          "    boost()\n"
                          "except UnboundLocalError:\n"
                          "    print('UnboundLocalError')"),
        transfer_prompt="What will running this code print?",
        transfer_choices=("15", "UnboundLocalError", "10", "Error: NameError"),
        correct_choice_index=1,
        explanation=("Even though 'score' exists in the global module scope, 'score += 5' inside boost() is an "
                     "assignment, which marks 'score' as local to boost(). Since it is read before assignment, "
                     "Python raises UnboundLocalError unless 'global score' is declared."),
    ),
)

EXERCISES = {e.id: e for e in (BASKET, LARGEST, TOTAL, CLOSURES, COUNTDOWN, SHALLOW_COPY, SCOPE_LEAK)}

