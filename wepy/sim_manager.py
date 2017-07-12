import sys

from wepy.resampling.resampler import NoResampler
from wepy.runner import NoRunner

class Manager(object):

    def __init__(self, init_walkers, num_workers,
                 runner = NoRunner(),
                 resampler = NoResampler(),
                 work_mapper = map):

        # the initial walkers
        self.init_walkers = init_walkers
        # the number of cores to use
        self.num_workers = num_workers
        # the runner is the object that runs dynamics
        self.runner = runner
        # the resampler
        self.resampler = resampler
        # the function for running work on the workers
        self.map = work_mapper

    def run_segment(self, walkers, segment_length, debug_prints=False):
        """Run a time segment for all walkers using the available workers. """

        # we need to count the number of things in the walkers without
        # keeping them in memory, we make a class that reads all the
        # things in the generator makes an index list and then puts
        # the contents back into a generator
        class CountingIterator(object):
            def __init__(self, iterable):
                self.indices = []
                self.iterable = self.count(iterable)

            def count(self, iterable):
                xs = []
                for i, x in enumerate(iterable):
                    self.indices.append(i)
                    xs.append(x)
                return (x for x in xs)

        counting_it = CountingIterator(walkers)
        walkers = counting_it.iterable
        indices = counting_it.indices

        if debug_prints:
            sys.stdout.write("Starting segment\n")

        new_walkers = list(self.map(self.runner.run_segment,
                                    walkers,
                                    (segment_length for i in indices)
                                   )
                          )
        if debug_prints:
            sys.stdout.write("Ending segment\n")

        return new_walkers

    def run_simulation(self, n_cycles, segment_lengths, debug_prints=False):
        """Run a simulation for a given number of cycles with specified
        lengths of MD segments in between.

        Can either return results in memory or write to a file.
        """

        if debug_prints:
            sys.stdout.write("Starting simulation\n")
        walkers = self.init_walkers
        walker_records = [[walker for walker in walkers]]
        resampling_records = []
        for cycle_idx in range(n_cycles):

            if debug_prints:
                sys.stdout.write("Begin cycle {}\n".format(cycle_idx))

            # run the segment
            new_walkers = self.run_segment(walkers, segment_lengths[cycle_idx],
                                           debug_prints=debug_prints)

            if debug_prints:
                sys.stdout.write("End cycle {}\n".format(cycle_idx))

            # record changes in state of the walkers
            walker_records.append(new_walkers)

            # resample based walkers
            resampled_walkers, cycle_resampling_records = self.resampler.resample(new_walkers)
            # save how the walkers were resampled
            resampling_records.append(cycle_resampling_records)
            # prepare resampled walkers for running new state changes
            walkers = resampled_walkers


        return walker_records, resampling_records