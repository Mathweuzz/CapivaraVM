class BaseV {
    int v;
    BaseV() { v = 1; }
    int inc() { return v + 1; }
}

public class VirtCall extends BaseV {
    VirtCall() { super(); }
    int inc() { return v + 2; } // override

    public static int run() {
        VirtCall c = new VirtCall();
        return c.inc(); // invokevirtual → 3
    }
}
