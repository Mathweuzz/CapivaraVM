class BaseS {
    static int f(int x) { return x + 1; }
}

public class InheritStatic extends BaseS {
    public static int run() {
        // chamada estática "herdada": o compilador resolve para invokestatic BaseS.f:(I)I
        return f(9); // 10
    }
}
