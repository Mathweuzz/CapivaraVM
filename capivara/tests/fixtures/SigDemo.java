public class SigDemo {
    static int f(int a, long b, String[] s) {
        return a + (int) b + (s == null ? 0 : s.length);
    }
    public static void main(String[] args) { }
}