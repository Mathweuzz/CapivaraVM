public class FlowOps {
    public static int run() {
        int x = 3;
        x = -x; // ineg -> -3
        if (x != -3) { //ifne
            return 0;
        }
        int y = 0;
        y++; // iinc -> 1
        // testa aritmetica e resto
        int a = 7, b = 3;
        int q = a / b; // idiv -> 2
        int r = a % b; // irem -> 1
        if (q == 2 && r == 1 && y == 1){
            return 1;
        }
        return 0;
    }
}