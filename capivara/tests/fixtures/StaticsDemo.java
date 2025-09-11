public class StaticsDemo {
    static int S; // default 0; neste passo não rodamos <clinit> automaticamente

    public static int run() {
        S = 7;         // putstatic
        return S;      // getstatic
    }
}
