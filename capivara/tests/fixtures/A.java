public class A {
    static final int C = 7;      // ConstantValue -> deve ser inicializado no linking
    static int X = 1;            // NÃO-final: só via <clinit>, fica default até executarmos
    static { X = 99; }           // <clinit> (não executado neste passo)
}