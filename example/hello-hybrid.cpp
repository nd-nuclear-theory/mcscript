// hello-hybrid.cpp
//
// Hybrid MPI/OpenMP hello world program.
//
// References:
//   http://www.slac.stanford.edu/comp/unix/farm/mpi_and_openmp.html
//   https://en.wikipedia.org/wiki/List_of_English_terms_of_venery,_by_animal
//
// Example:
//
//   Compilation/invocation:
//
//     mpicxx -fopenmp hello-hybrid.cpp -o hello-hybrid
//     setenv OMP_NUM_THREADS 4
//     mpirun -n 2 -x OMP_NUM_THREADS ./hello-hybrid
//
//   Output:
//
//     Hello from ... colony 0 / 2 : bunny rabbit 1 / 4 : warren mac03
//     Hello from ... colony 0 / 2 : bunny rabbit 0 / 4 : warren mac03
//     Hello from ... colony 0 / 2 : bunny rabbit 2 / 4 : warren mac03
//     Hello from ... colony 0 / 2 : bunny rabbit 3 / 4 : warren mac03
//     Hello from ... colony 1 / 2 : bunny rabbit 1 / 4 : warren mac03
//     Hello from ... colony 1 / 2 : bunny rabbit 2 / 4 : warren mac03
//     Hello from ... colony 1 / 2 : bunny rabbit 0 / 4 : warren mac03
//     Hello from ... colony 1 / 2 : bunny rabbit 3 / 4 : warren mac03
//
// Language: C++11
//
// Mark A. Caprio and Anna E. McCoy
// University of Notre Dame
//
// 4/22/17 (mac): Created.

#include <cstdlib>
#include <iostream>

#include "mpi.h"
#include <omp.h>

int main(int argc, char **argv)
{

  // MPI setup

  MPI_Init(&argc,&argv);
  int num_processes, rank;
  char processor_name[MPI_MAX_PROCESSOR_NAME];
  int processor_name_len;
  MPI_Comm_size(MPI_COMM_WORLD,&num_processes);
  MPI_Comm_rank(MPI_COMM_WORLD,&rank);
  MPI_Get_processor_name(processor_name,&processor_name_len);

  // say hello to world
  #pragma omp parallel
  {
    int num_threads = omp_get_num_threads();
    int thread_num = omp_get_thread_num();
    
    #pragma omp critical
    std::cout
      << "Hello from ... colony " << rank << " / " << num_processes << " : "
      << "bunny rabbit " << thread_num << " / " << num_threads << " : "
      << "warren " << processor_name
      << std::endl;
  }

  // termination
  MPI_Finalize();
  return EXIT_SUCCESS;

}
