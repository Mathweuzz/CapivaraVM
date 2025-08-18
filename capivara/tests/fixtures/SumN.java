public class SumN {
    // metodo de entrada para este passo: static, sem args, retorn int
    public static int run() {
        int n = 5;
        int s = 0;
        int i = 1;
        while (i <= n) {
            s = s + i; // iadd
            i++; //iinc
        }
        return s; // ireturn
    }
}