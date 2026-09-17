#include <stdlib.h>
#include <stdio.h>
#define N (1<<20)
static double a[N], b[N];
int main(void){
  double s=0;
  for(int it=0; it<40; it++){
    for(int i=0;i<N;i++){ a[i]=b[i]*0.5+i; }
    for(int i=0;i<N;i++){ b[i]=a[i]+1.0; s+=b[i]; }
  }
  printf("%f\n", s);
  return 0;
}
