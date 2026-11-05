n = int(input())
a = list(map(int, input().split()))
total = 0
for x in a:
    total -= x
print(total)
