using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Diagnostics;

using static IT2AMK.Util.Util;
using IT2AMK.IT;

namespace IT2AMK.Conv
{
	abstract class Resampler
	{
		protected List<int> taps;

		public virtual Sample resample(Sample sample, double new_length)
		{
			Debug.Assert(new_length > 0);

			sample.trim();
			sample.expand_ping_loop();
			var new_sample = new Sample(sample);
			new_sample.clear_sample_data();

			if (!sample.looped || sample.loop_start >= sample.loop_end) {
				_resample_unlooped(sample, new_sample, new_length);
			} else {
				_resample_looped(sample, new_sample, new_length);
			}

			return new_sample;
		}

		protected virtual void _resample_unlooped(Sample sample, Sample new_sample, double new_length)
		{
			double multiplier = sample.length / new_length;

			int index = 0;
			for (double stepper = 0.0; stepper < sample.length; stepper += multiplier) {
				var indexes = new List<int>();
				for (int i = 0; i < taps.Count; i++) {
					int ii = min(taps[i] + ifloor(stepper), sample.length - 1);
					indexes.Add(ii);
				}

				new_sample.add_sample_point(_interpolate(sample, stepper - Math.Floor(stepper), indexes.ToArray(), ifloor(stepper)));
				index++;
			}
			new_sample.c5_speed = (int)(sample.c5_speed / multiplier);

			//show_verbose("Padding zeros at end to multiple of 16 length...");
			while (new_sample.length % 16 != 0)
				new_sample.add_sample_point(new SamplePoint(0));
		}

		protected virtual void _resample_looped(Sample sample, Sample new_sample, double new_length)
		{
			double multiplier = sample.length / new_length;
			double diff = (sample.loop_end - sample.loop_start) / multiplier;
			double offset = 0.0;

			if (diff != Math.Floor(diff)) {
				new_length *= Math.Ceiling(diff) / diff;
				multiplier = sample.length / new_length;
				offset = (Math.Ceiling(new_length) - new_length) * -multiplier;
			}

			int loop_length = (int)Math.Ceiling(diff);

			// First calculate how long the sample would be if we stretched it to match %16==0
			double stretch_length = new_length;
			if (loop_length % 16 != 0) {
				int stretch_loop_length = loop_length + 16 - loop_length%16;
				stretch_length *= (double)stretch_loop_length / loop_length;
			}

			// Then calculate how long the sample would be if we instead repeated the looped portion to match %16==0
			double repeat_length = new_length;
			int repeat_loop_length = loop_length;
			while (repeat_loop_length % 16 != 0) {
				repeat_loop_length += loop_length;
				repeat_length += loop_length;
			}

			// If the repeated case is shorter, then let's repeat the looped part
			if (repeat_length < stretch_length && repeat_length != new_length) {
				//show_verbose("Repeating looped portion of sample to multiple of 16 length...");

				multiplier = sample.length / new_length;
				offset = (Math.Ceiling(new_length) - new_length) * -multiplier;
				
				repeat_length = new_length;
				repeat_loop_length = loop_length;
				while (repeat_loop_length % 16 != 0) {
					int old_length = sample.length;
					for (int i = sample.loop_start; i < old_length; i++)
						sample.add_sample_point(sample.sample_data[i]);
					repeat_loop_length += loop_length;
					repeat_length += loop_length;
				}
				new_length = repeat_length;
			} else if (stretch_length != new_length) {
				//show_verbose("Stretching sample to multiple of 16 length...");
				new_length = stretch_length;
				multiplier = sample.length / new_length;
				offset = (Math.Ceiling(new_length) - new_length) * -multiplier;
			}

			int index = 0;
			for (double stepper = offset; stepper < sample.length; stepper += multiplier) {
				var indexes = new List<int>();
				var indexes_l = new List<int>();

				for (int i = 0; i < taps.Count; i++) {
					int ii = taps[i] + ifloor(stepper);
					while (ii >= sample.length)
						ii -= (sample.length - sample.loop_start);
					indexes.Add(ii);

					if (ifloor(stepper) >= sample.loop_start && ii < sample.loop_start)
						indexes_l.Add(ii + (sample.length - sample.loop_start));
					else
						indexes_l.Add(ii);
				}

				var sp = _interpolate(sample, stepper - Math.Floor(stepper), indexes.ToArray(), ifloor(stepper));
				var sp2 = _interpolate(sample, stepper - Math.Floor(stepper), indexes_l.ToArray(), ifloor(stepper));
				new_sample.add_sample_point((sp + sp2) / 2);
				index++;
			}

			new_sample.loop_start = (int)(Math.Ceiling(sample.loop_start / multiplier));
			new_sample.loop_end = (int)Math.Ceiling(new_length);
			new_sample.c5_speed = (int)(sample.c5_speed / multiplier);

			new_sample.trim();
			//show_verbose("Padding zeros at start to multiple of 16 length...");
			new_sample.pad_left();
		}

		protected abstract SamplePoint _interpolate(Sample sample, double stepper, int[] indexes, int index);

		protected virtual void _determine_loop_points(Sample sample, Sample new_sample, int index, double stepper)
		{
			if (stepper <= sample.loop_start)
				new_sample.loop_start = index;
			if (stepper <= sample.loop_end)
				new_sample.loop_end = index;
			if (stepper <= sample.sus_loop_start)
				new_sample.sus_loop_start = index;
			if (stepper <= sample.sus_loop_end)
				new_sample.sus_loop_end = index;
		}
	}

	class NearestNeighborResampler : Resampler
	{
		public NearestNeighborResampler()
		{
			taps = new List<int>(new int[] {0, 1});
		}

		protected override SamplePoint _interpolate(Sample sample, double frac, int[] indexes, int index)
		{
			Debug.Assert(!sample.looped || sample.loop_end > sample.loop_start);
			Debug.Assert(indexes.Length == 2);

			var sample_points = new SamplePoint[indexes.Length];
			for (int i = 0; i < indexes.Length; i++)
				sample_points[i] = sample.sample_data[max(indexes[i], 0)];
			
			return (frac < 0.5) ? sample_points[0] : sample_points[1];
		}
	}

	class LinearResampler : Resampler
	{
		public LinearResampler()
		{
			taps = new List<int>(new int[] {0, 1});
		}

		protected override SamplePoint _interpolate(Sample sample, double frac, int[] indexes, int index)
		{
			Debug.Assert(!sample.looped || sample.loop_end > sample.loop_start);
			Debug.Assert(indexes.Length == 2);

			var sample_points = new SamplePoint[indexes.Length];
			for (int i = 0; i < indexes.Length; i++)
				sample_points[i] = sample.sample_data[max(indexes[i], 0)];
			
			return new SamplePoint
			{
				left = (int)Math.Floor((1 - frac) * sample_points[0].left + frac * sample_points[1].left + 0.5),
				right = (int)Math.Floor((1 - frac) * sample_points[0].right + frac * sample_points[1].right + 0.5)
			};
		}
	}

	class CubicResampler : Resampler
	{
		public CubicResampler()
		{
			taps = new List<int>(new int[] {-1, 0, 1, 2});
		}

		protected override SamplePoint _interpolate(Sample sample, double frac, int[] indexes, int index)
		{
			Debug.Assert(!sample.looped || sample.loop_end > sample.loop_start);
			Debug.Assert(indexes.Length == 4);

			var sample_points = new SamplePoint[indexes.Length];
			for (int i = 0; i < indexes.Length; i++)
				sample_points[i] = sample.sample_data[max(indexes[i], 0)];

			var u = frac;
			var p = sample_points;

			return new SamplePoint
			{
				left = (int)Math.Floor(((u*u*(2-u)-u)*p[0].left + (u*u*(3*u-5)+2)*p[1].left + (u*u*(4-3*u)+u)*p[2].left
					   + u*u*(u-1)*p[3].left)/2 + 0.5),
				right = (int)Math.Floor(((u*u*(2-u)-u)*p[0].right + (u*u*(3*u-5)+2)*p[1].right
					    + (u*u*(4-3*u)+u)*p[2].right + u*u*(u-1)*p[3].right)/2 + 0.5)
			};
		}
	}

	class SincResampler : Resampler
	{
		protected int _sinc_points;

		public SincResampler(int sinc_points)
		{
			Debug.Assert(sinc_points > 0);
			_sinc_points = sinc_points;
			taps = new List<int>();
			for (int i = -sinc_points/2; i < sinc_points/2; i++)
				taps.Add(i);
		}

		protected override SamplePoint _interpolate(Sample sample, double frac, int[] indexes, int index)
		{
			Debug.Assert(!sample.looped || sample.loop_end > sample.loop_start);

			double left_sum = 0;
			double right_sum = 0;

			for (int i = 0; i < indexes.Length; i++) {
				int ii = indexes[i];
				if (ii >= 0 && (sample.looped || ii < sample.length)) {
					while (ii >= sample.length)
						ii -= (sample.length - sample.loop_start);

					left_sum += sample.sample_data[ii].left * sinc(frac - taps[i]);
					right_sum += sample.sample_data[ii].right * sinc(frac - taps[i]);
				}
			}

			return new SamplePoint
			{
				left = iround(left_sum),
				right = iround(right_sum)
			};
		}
	}
}
