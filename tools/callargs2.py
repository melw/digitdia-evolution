import sys, struct
B=0x80000000
d=open(sys.argv[1],'rb').read(); target=int(sys.argv[2],16)
W=struct.unpack('<%dI'%(len(d)//4),d[:len(d)//4*4])
JAL=0x0C000000|((target&0x0FFFFFFF)>>2)
def find_a0(i):
    # look at delay slot and up to 6 previous insns for writes to a0 (rt==4 for I-type, rd==4 for move)
    for k in [i+1]+list(range(i-1,i-8,-1)):
        x=W[k]; op=x>>26; rs=(x>>21)&31; rt=(x>>16)&31; imm=x&0xffff
        if op in (0xd,0x9) and rt==4:
            base=None
            if rs==0: base=0
            else:
                for m in range(k-1,k-400,-1):
                    y=W[m]
                    if (y>>26)==0xf and ((y>>16)&31)==rs: base=(y&0xffff)<<16; break
            if base is None: return None
            return base|imm if op==0xd else (base+(imm-0x10000 if imm&0x8000 else imm))&0xffffffff
        if op==0xf and rt==4: return imm<<16
    return None
def find_a1(i):
    for k in [i+1]+list(range(i-1,i-8,-1)):
        x=W[k]; op=x>>26; rs=(x>>21)&31; rt=(x>>16)&31; imm=x&0xffff
        if op==0x9 and rt==5 and rs==0: return "%#x"%(imm-0x10000 if imm&0x8000 else imm)
        if op==0xd and rt==5 and rs==0: return "%#x"%imm
        if op==0x23 and rt==5: return "lw[%d+%#x]"%(rs,imm)
        if op==0 and (x&0x3f)==0x21 and ((x>>11)&31)==5: return "reg%d"%(rs if rs else rt)
    return "?"
for i,w in enumerate(W):
    if w==JAL:
        a0=find_a0(i)
        print("%#010x  id=%s  val=%s"%(B+4*i, ("%#x"%a0) if a0 is not None else "?", find_a1(i)))
