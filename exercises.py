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

EXERCISES = {e.id: e for e in (BASKET, LARGEST, TOTAL)}
