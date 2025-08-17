public class CPDemo {
    static int XI = 42;

    static long keep() {
        return 1234567890123L;
    }

    public static void main(String[] args) {
        int a = 1 + 2;
        long l = keep();
        float f = 3.14f;
        double d = 2.71828;
        String s = "capivara";
        System.out.println(s + " " + a + " " + l + " " + f + " " + d);
    }
}