#include <stdio.h>

#define MAX_SIZE 100
#define ll long long

ll fibonacci(int n, ll cache[]) {
    if (n <= 1)
        return n;

    if (cache[n] != -1)
        return cache[n];

    cache[n] = fibonacci(n - 1, cache) + fibonacci(n - 2, cache);
    return cache[n];
}

void calculateFibonacci(int num) {
    ll cache[MAX_SIZE];
    for (int i = 0; i < MAX_SIZE; i++)
        cache[i] = -1;

    printf("Fibonacci Series: ");
    for (int i = 0; i < num; i++) {
        printf("%lld ", fibonacci(i, cache));
    }
    printf("\n");
}

int main() {
    int num;
    printf("Enter the number of Fibonacci terms to calculate: ");
    scanf("%d", &num);

    calculateFibonacci(num);

    return 0;
}