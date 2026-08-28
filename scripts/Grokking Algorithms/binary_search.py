def binary_search(list, item):
  # Za pomocą low i high kontrolujemy, która część listy jest przeszukiwana.
  low = 0
  high = len(list) - 1

  # Dopóki obszar poszukiwań nie został zawężony do jednego elementu...
  while low <= high:
    # ...wybieramy środkowy element.
    mid = (low + high) // 2
    guess = list[mid]
    # Znaleziono element.
    if guess == item:
      return mid
    # Strzelono za dużą liczbę.
    if guess > item:
      high = mid - 1
    # Strzelono za małą liczbę.
    else:
      low = mid + 1

  # Element nie istnieje.
  return None

my_list = [1, 3, 5, 7, 9]
print binary_search(my_list, 3) # => 1

# Wartość None w Pythonie oznacza nic, czyli wskazuje, że elementu nie znaleziono.
print binary_search(my_list, -1) # => None
