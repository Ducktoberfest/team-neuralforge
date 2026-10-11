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
           "How can you bind the current loop value of 'i' into each function's default arguments at creation time?"),
    forbidden=(r"\bi\s*=\s*i\b", r"\bdefault\s+(argument|parameter)", r"\blate\s+binding\b"),
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
)

EXERCISES = {e.id: e for e in (BASKET, LARGEST, TOTAL, CLOSURES, COUNTDOWN)}

