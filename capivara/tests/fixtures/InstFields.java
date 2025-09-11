public class InstFields {
    int x;
    int y;
    public InstFields() { this.x = 2; this.y = 3; }

    public static int run() {
        InstFields p = new InstFields(); // new, dup, invokespecial <init>
        p.x = 10;                        // putfield
        return p.x + p.y;                // getfield + iadd -> 13
    }

    int sum() { return x + y; }         // para invokevirtual
}
