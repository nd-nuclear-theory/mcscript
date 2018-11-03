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
//     mpirun -n 2 ./hello-hybrid
//
//   If your implementation of mpirun does not by default pass all environment
//   variables to the executable, you may have to check what option to use to
//   pass through the OMP_NUM_THREADS variable, e.g.,
//
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
// 04/22/17 (mac): Created.
// 02/22/18 (mac): Report stack size.
// 07/06/18 (pjf): Initialize MPI correctly (with threading).

#include <cstdlib>
#include <iostream>
#include <iomanip>

#include "mpi.h"
#include <omp.h>

int main(int argc, char **argv)
{

  std::cout << "Initializing MPI..." << std::endl;

  // MPI setup

  int provided;
  MPI_Init_thread(&argc,&argv,MPI_THREAD_SERIALIZED, &provided);
  if (provided < MPI_THREAD_SERIALIZED) {
    std::cerr << "MPI does not provided needed threading level" << std::endl;
    exit(1);
  }
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

    // print greeting
    #pragma omp critical
    std::cout
      << "Hello from ... colony " << rank << " / " << num_processes << " : "
      << "bunny rabbit " << std::setw(2) << thread_num << " / " << std::setw(2) << num_threads << " : "
      << "warren " << processor_name
      << std::endl;

    // report stack size from Intel OpenMP extensions
    #ifdef __INTEL_COMPILER
    #pragma omp barrier
    #pragma omp master
    if (rank==0)
      {
        std::cout
          << std::endl
          << "The chief bunny rabbit reports a stack size of " << kmp_get_stacksize_s() << " bytes."
          << std::endl;
      }
    #endif
  }

  // termination
  MPI_Finalize();
  return EXIT_SUCCESS;

}
