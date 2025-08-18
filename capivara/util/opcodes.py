# ===== Constant Pool tags =====
CP_Utf8               = 1
CP_Integer            = 3
CP_Float              = 4
CP_Long               = 5
CP_Double             = 6
CP_Class              = 7
CP_String             = 8
CP_Fieldref           = 9
CP_Methodref          = 10
CP_InterfaceMethodref = 11
CP_NameAndType        = 12
CP_MethodHandle       = 15
CP_MethodType         = 16
CP_InvokeDynamic      = 18

# ===== Bytecodes essenciais  =====
NOP        = 0x00

ICONST_M1  = 0x02
ICONST_0   = 0x03
ICONST_1   = 0x04
ICONST_2   = 0x05
ICONST_3   = 0x06
ICONST_4   = 0x07
ICONST_5   = 0x08

BIPUSH     = 0x10
SIPUSH     = 0x11

ILOAD      = 0x15
LLOAD      = 0x16  
FLOAD      = 0x17 
DLOAD      = 0x18 
ALOAD      = 0x19 

ILOAD_0    = 0x1a
ILOAD_1    = 0x1b
ILOAD_2    = 0x1c
ILOAD_3    = 0x1d

ISTORE     = 0x36
ISTORE_0   = 0x3b
ISTORE_1   = 0x3c
ISTORE_2   = 0x3d
ISTORE_3   = 0x3e

IADD       = 0x60
ISUB       = 0x64
IMUL       = 0x68
IDIV       = 0x6c
IREM       = 0x70
INEG       = 0x74
IINC       = 0x84

IFEQ       = 0x99
IFNE       = 0x9a
IFLT       = 0x9b
IFGE       = 0x9c
IFGT       = 0x9d
IFLE       = 0x9e

IF_ICMPEQ  = 0x9f
IF_ICMPNE  = 0xa0
IF_ICMPLT  = 0xa1
IF_ICMPGE  = 0xa2
IF_ICMPGT  = 0xa3
IF_ICMPLE  = 0xa4

GOTO       = 0xa7

IRETURN    = 0xac
LRETURN    = 0xad 
FRETURN    = 0xae 
DRETURN    = 0xaf 
ARETURN    = 0xb0 
RETURN     = 0xb1
