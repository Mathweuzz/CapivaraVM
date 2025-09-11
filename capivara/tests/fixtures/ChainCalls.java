public class ChainCalls {
    static int add2(int x) { return x + 2; }
    static int mul3(int x) { return x * 3; }

    public static int run() {
        int v = 4;
        v = add2(v);
        v = mul3(v);
        return v; // (4+2)*3 = 18
    }
}
