#define MAX_SIZE 100
#define ll long long

typedef struct {
    int current;
    int next;
} Fibonacci;

struct Fibonacci2 {
    int current;
    int next;
};

void fibonacciSequence(Fibonacci* fib, int n);

int main() {
    int a;
    Fibonacci fib;
    Fibonacci fib2 = {1, 0};
    Fibonacci* fib_ref = &fib;

    (*fib_ref).current = 0;
    fib.next = 1;

    ll n = 100000000000000;  // Number of Fibonacci numbers to generate

//    fibonacciSequence(&fib, n);

    return 0;
}

//void fibonacciSequence(Fibonacci* fib, int n) {
//    int i;
//    for (i = 0; i < n; i++) {
//        int current = fib->current;
//        int next = fib->next;
//
//        // Calculate the next Fibonacci number
//        int temp = current;
//        current = next;
//        next = temp + next;
//
//        fib->current = current;
//        fib->next = next;
//    }
//}