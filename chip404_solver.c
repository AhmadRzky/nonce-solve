// Chip404 free-mint PoW solver (fleet version): keccak256(salt32 || addr20 || nonce32BE) <= target
// salt = keccak256("chip404.trial.v1"), wallet fixed. Supports full 64-bit nonce.
// Primary target = strict (argv[3]). Optional secondary target (argv[7], looser/easier than
// primary): hashes that satisfy the loose target but not the strict one are appended
// immediately to the file at argv[8] (line: "nonce=<n> hash=<hex>") and the search continues.
// Usage: solver <salt_hex64> <wallet_hex40> <target_hex64> <nthreads> <seconds> <offset> [loose_hex64 secondary_path]
// seconds==0 -> verify mode: print hash of nonce=offset only.
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <pthread.h>
#include <time.h>
#include <stdatomic.h>
#include <fcntl.h>
#include <unistd.h>

static const uint64_t RC[24]={0x0000000000000001ULL,0x0000000000008082ULL,0x800000000000808aULL,0x8000000080008000ULL,0x000000000000808bULL,0x0000000080000001ULL,0x8000000080008081ULL,0x8000000000008009ULL,0x000000000000008aULL,0x0000000000000088ULL,0x0000000080008009ULL,0x000000008000000aULL,0x000000008000808bULL,0x800000000000008bULL,0x8000000000008089ULL,0x8000000000008003ULL,0x8000000000008002ULL,0x8000000000000080ULL,0x000000000000800aULL,0x800000008000000aULL,0x8000000080008081ULL,0x8000000000008080ULL,0x0000000080000001ULL,0x8000000080008008ULL};
static const int ROTC[24]={1,3,6,10,15,21,28,36,45,55,2,14,27,41,56,8,25,43,62,18,39,61,20,44};
static const int PILN[24]={10,7,11,17,18,3,5,16,8,21,24,4,15,23,19,13,12,2,20,14,22,9,6,1};
#define ROL(x,n) (((x)<<(n))|((x)>>(64-(n))))
static inline void keccakf(uint64_t st[25]){
 for(int round=0;round<24;round++){
  uint64_t C[5],t;
  for(int i=0;i<5;i++) C[i]=st[i]^st[i+5]^st[i+10]^st[i+15]^st[i+20];
  for(int i=0;i<5;i++){ t=C[(i+4)%5]^ROL(C[(i+1)%5],1); for(int j=0;j<25;j+=5) st[j+i]^=t; }
  t=st[1];
  for(int i=0;i<24;i++){ int j=PILN[i]; uint64_t u=st[j]; st[j]=ROL(t,ROTC[i]); t=u; }
  for(int y=0;y<25;y+=5){ uint64_t row[5]; for(int x=0;x<5;x++) row[x]=st[y+x];
    for(int x=0;x<5;x++) st[y+x]=row[x]^((~row[(x+1)%5])&row[(x+2)%5]); }
  st[0]^=RC[round];
 }
}
static uint64_t fixed_lane[11];
static uint8_t target_bytes[32];
static uint8_t loose_bytes[32];
static int has_loose=0;
static char secondary_path[1024]="";
static atomic_int found_flag=0;
static atomic_ullong total_tried=0;
static uint64_t found_nonce=0;
static char found_hash_hex[65]="";

static inline int hash_le(const uint64_t st_out[25], const uint8_t tgt[32]){
 for(int i=0;i<32;i++){
   uint8_t b=(uint8_t)(st_out[i/8]>>(8*(i%8)));
   if(b<tgt[i]) return 1;
   if(b>tgt[i]) return 0;
 }
 return 1;
}
static inline void hash_hex(const uint64_t st_out[25], char out[65]){
 static const char*H="0123456789abcdef";
 for(int i=0;i<32;i++){ uint8_t b=(uint8_t)(st_out[i/8]>>(8*(i%8))); out[2*i]=H[b>>4]; out[2*i+1]=H[b&15]; }
 out[64]=0;
}
static void record_secondary(uint64_t nonce, const uint64_t st[25]){
 char hx[65]; hash_hex(st,hx);
 char line[160]; int n=snprintf(line,sizeof line,"nonce=%llu hash=%s\n",(unsigned long long)nonce,hx);
 int fd=open(secondary_path,O_APPEND|O_CREAT|O_WRONLY,0644);
 if(fd>=0){ ssize_t w=write(fd,line,n); (void)w; close(fd); }
}
typedef struct{ uint64_t start; uint64_t stride; int tid; long seconds; } Job;
static void* worker(void*arg){
 Job*j=(Job*)arg; uint64_t nonce=j->start; uint64_t local=0;
 struct timespec ts0,ts1; clock_gettime(CLOCK_MONOTONIC,&ts0);
 while(!atomic_load(&found_flag)){
   for(int k=0;k<4096;k++){
     uint64_t st[25]; memset(st,0,sizeof st);
     for(int i=0;i<9;i++) st[i]=fixed_lane[i];
     uint64_t n=nonce;
     uint64_t lane9 = fixed_lane[9];
     lane9 |= ((uint64_t)((n>>32)&0xffULL))<<56;
     lane9 |= ((uint64_t)((n>>40)&0xffULL))<<48;
     lane9 |= ((uint64_t)((n>>48)&0xffULL))<<40;
     lane9 |= ((uint64_t)((n>>56)&0xffULL))<<32;
     st[9]=lane9;
     uint64_t lane10=0;
     lane10 |= (uint64_t)((n>>24)&0xffULL);
     lane10 |= ((uint64_t)((n>>16)&0xffULL))<<8;
     lane10 |= ((uint64_t)((n>>8)&0xffULL))<<16;
     lane10 |= (uint64_t)(n&0xffULL)<<24;
     lane10 |= (uint64_t)0x01ULL<<32;
     st[10]=lane10;
     st[16]=0x8000000000000000ULL;
     keccakf(st);
     local++;
     if(hash_le(st,target_bytes)){ found_nonce=n; hash_hex(st,found_hash_hex); atomic_store(&found_flag,1); atomic_fetch_add(&total_tried,local); return NULL; }
     if(has_loose && hash_le(st,loose_bytes)) record_secondary(n,st);
     nonce+=j->stride;
   }
   atomic_fetch_add(&total_tried,local); local=0;
   if(j->seconds>0){ clock_gettime(CLOCK_MONOTONIC,&ts1); if(ts1.tv_sec-ts0.tv_sec>=j->seconds) break; }
 }
 return NULL;
}
static void parse_hex32(const char*s, uint8_t out[32]){
 for(int i=0;i<32;i++) out[i]=(uint8_t)strtoul((char[]){s[2*i],s[2*i+1],0},NULL,16);
}
int main(int argc,char**argv){
 // args: salt_hex(64) wallet_hex(40) target_hex(64) nthreads seconds start_offset [loose_hex(64) secondary_path]
 if(argc<7){ fprintf(stderr,"usage: solver salt wallet target nthreads seconds offset [loose secondary_path]\n"); return 2; }
 uint8_t salt[32],addr[20];
 parse_hex32(argv[1],salt);
 for(int i=0;i<20;i++) addr[i]=(uint8_t)strtoul((char[]){argv[2][2*i],argv[2][2*i+1],0},NULL,16);
 parse_hex32(argv[3],target_bytes);
 int nthreads=atoi(argv[4]); long seconds=atol(argv[5]); uint64_t offset=strtoull(argv[6],NULL,10);
 if(argc>=9){ parse_hex32(argv[7],loose_bytes); snprintf(secondary_path,sizeof secondary_path,"%s",argv[8]); has_loose=1; }
 uint8_t payload[84]; memcpy(payload,salt,32); memcpy(payload+32,addr,20); memset(payload+52,0,32);
 for(int L=0;L<11;L++){ uint64_t v=0; for(int b=0;b<8;b++){ int idx=L*8+b; if(idx<84) v|=((uint64_t)payload[idx])<<(8*b); } fixed_lane[L]=v; }
 if(seconds==0){
   uint64_t st[25]; memset(st,0,sizeof st); for(int i=0;i<9;i++) st[i]=fixed_lane[i];
   uint64_t n=offset; uint64_t lane9=fixed_lane[9];
   lane9 |= ((uint64_t)((n>>32)&0xffULL))<<56; lane9 |= ((uint64_t)((n>>40)&0xffULL))<<48; lane9 |= ((uint64_t)((n>>48)&0xffULL))<<40; lane9 |= ((uint64_t)((n>>56)&0xffULL))<<32; st[9]=lane9;
   uint64_t lane10=0; lane10|=(uint64_t)((n>>24)&0xffULL); lane10|=(uint64_t)((n>>16)&0xffULL)<<8; lane10|=(uint64_t)((n>>8)&0xffULL)<<16; lane10|=(uint64_t)(n&0xffULL)<<24; lane10|=(uint64_t)0x01ULL<<32; st[10]=lane10; st[16]=0x8000000000000000ULL;
   keccakf(st);
   char hx[65]; hash_hex(st,hx); printf("%s\n",hx); return 0;
 }
 pthread_t th[32]; Job jobs[32];
 struct timespec t0,t1; clock_gettime(CLOCK_MONOTONIC,&t0);
 for(int i=0;i<nthreads;i++){ jobs[i]=(Job){.start=offset+i,.stride=(uint64_t)nthreads,.tid=i,.seconds=seconds}; pthread_create(&th[i],NULL,worker,&jobs[i]); }
 for(int i=0;i<nthreads;i++) pthread_join(th[i],NULL);
 clock_gettime(CLOCK_MONOTONIC,&t1);
 double el=(t1.tv_sec-t0.tv_sec)+(t1.tv_nsec-t0.tv_nsec)/1e9;
 unsigned long long tried=atomic_load(&total_tried);
 printf("elapsed=%.2f tried=%llu rate=%.0f found=%d",el,tried, tried/el, (int)atomic_load(&found_flag));
 if(atomic_load(&found_flag)) printf(" nonce=%llu hash=%s",(unsigned long long)found_nonce,found_hash_hex);
 printf("\n");
 return atomic_load(&found_flag)?42:0;
}
