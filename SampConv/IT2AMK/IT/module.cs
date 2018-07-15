using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Diagnostics;
using System.IO;

using IT2AMK.Util;
using static IT2AMK.Util.Util;

namespace IT2AMK.IT
{
	class Module
	{
		private List<Pattern> _patterns = new List<Pattern>();
		private List<Sample> _samples = new List<Sample>();
		private List<Instrument> _instruments = new List<Instrument>();
		private List<int> _orders = new List<int>();
		private List<Channel> _channels = new List<Channel>();

		public string title {get; private set;}
		public string author {get; private set;}
		public string message {get; private set;}

		public bool stereo {get; private set; }
		public bool use_instruments {get; private set;}

		public int global_volume {get; private set;}
		public int sample_volume {get; private set;}
		public int init_speed {get; private set;}
		public int init_tempo {get; private set;} 

		public int rows_per_beat {get; private set;} 
		public int rows_per_measure {get; private set;} 

		public ReadOnlyCollection<Pattern> patterns { get { return _patterns.AsReadOnly(); } }
		public ReadOnlyCollection<Sample> samples { get { return _samples.AsReadOnly(); } }
		public ReadOnlyCollection<Instrument> instruments { get { return _instruments.AsReadOnly(); } }
		public ReadOnlyCollection<int> orders { get { return _orders.AsReadOnly(); } }
		public ReadOnlyCollection<Channel> channels { get { return _channels.AsReadOnly(); } }

		public Module(string filename)
		{
			load(filename);
		}

		public void load(string filename)
		{
			try {
				show_message("Loading module: \"{0}\"...", filename);
				byte[] data = File.ReadAllBytes(filename);

				if (to_string(data, 0, 4) != "IMPM") {
					throw new InvalidFileException("This is not a valid IT module file.");
				}

				int ord_num = to_uint16(data, 0x20);
				int ins_num = to_uint16(data, 0x22);
				int smp_num = to_uint16(data, 0x24);
				int pat_num = to_uint16(data, 0x26);
				
				int flags = to_uint16(data, 0x2C);
				int special = to_uint16(data, 0x2E);

				stereo = (flags & 0x1) > 0;
				use_instruments = (flags & 0x4) > 0;
				bool has_message = (special & 0x1) > 0;

				global_volume = data[0x30];
				sample_volume = data[0x31];
				init_speed = data[0x32];
				init_tempo = data[0x33];

				_load_metadata(data, has_message);
				_init_channels(data);

				for (int i = 0; i < ord_num; i++)
					_orders.Add(data[0xC0 + i]);

				show_message("Loading samples...");
				for (int i = 0; i < smp_num; i++)
					_samples.Add(new Sample(data, to_int32(data, 0xC0 + ord_num + 4*ins_num + 4*i), i));

			} catch (FileNotFoundException) {
				throw new FileNotFoundException("The file: \"" + filename + "\" could not be found.");
			} catch (FileLoadException) {
				throw new FileLoadException("The file: \"" + filename + "\" could not be loaded. " +
											"(Maybe another program has it open?)");
			} catch (ArgumentOutOfRangeException) {
				throw new InvalidFileException("This is not a valid IT module file (Out of range error).");
			} catch (IndexOutOfRangeException) {
				throw new InvalidFileException("This is not a valid IT module file (Out of range error).");
			}
		}

		private void _load_metadata(byte[] data, bool has_message)
		{
			title = to_string(data, 4, 26);
			rows_per_beat = data[0x1E];
			rows_per_measure = data[0x1F];

			int message_length = to_uint16(data, 0x36);
			message = (has_message) ? to_string(data, to_int32(data, 0x38), message_length) : "";
		}

		private void _init_channels(byte[] data)
		{
			for (int i = 0; i < 64; i++) {
				_channels.Add(new Channel());
				_channels[i].volume = data[0x80 + i];
				int panning = data[0x40 + i];
				if (panning == 100) {
					_channels[i].surround = true;
					_channels[i].panning = 32;
					_channels[i].enabled = true;
				} else {
					_channels[i].panning = min(panning & 0x7F, 64);
					_channels[i].enabled = (panning >= 128) ? false : true;
					_channels[i].surround = false;
				}
			}
		}
	}

	class Channel
	{
		public string name = "";
		public int volume = 64;
		public int panning = 32;
		public bool surround = false;
		public bool enabled = true;
	}

	class InvalidFileException : Exception
	{
		public InvalidFileException()
		{
		}

		public InvalidFileException(string message)
		: base(message)
		{
		}

		public InvalidFileException(string message, Exception inner)
		: base(message, inner)
		{
		}
	}

	class UnsupportedFeatureException : Exception
	{
		public UnsupportedFeatureException()
		{
		}

		public UnsupportedFeatureException(string message)
		: base(message)
		{
		}

		public UnsupportedFeatureException(string message, Exception inner)
		: base(message, inner)
		{
		}
	}
}
