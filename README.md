## Workflow
- Install python if it isn't already installed on your computer
- Clone (or download) this repo and put it in the directory AddMusicK is in
- [Open a command prompt](https://youtu.be/bgSSJQolR0E?t=47) in this folder
- type `python it2amk.py modules/yourmodule.it`
- A file named `yourmodule.txt` should appear in the `music` directory, and a folder called `yourmodule` full of BRRs should appear in the `samples` directory.
- Copy the text file to AMK's music folder, and the `yourmodule` samples folder into AMK's sample folder.
  - `AddMusicK/it2amk/music/your_module.txt` to `AddMusicK/music`
  - `AddMusicK/it2amk/samples/your_module/` to `AddMusicK/samples/your_module/`
- Run AMK, or the AMK GUI in porting mode if you're more used to that. 
- Spend some time refining the MML file, turning repeated note patterns into loops, and overall optimizing things and fixing inaccuracies

## Commands that can be used in module comments
`author "Author Name"`

`game "Game Name"`

`length "m:ss"`

`legato True or False` - Specifies whether or not to apply $F4 $02 (True by default)

`echo XXYYLLRR` - Specifies the echo flags. XX = Delay, WW = Feedback, LL = Echo left volume, RR = Echo right volume

`fir 1122334455667788` - Specifies the 8 byte FIR coefficients

`tmult n` - Specifies the tempo and note length multiplier for the song. Decimals allowed. Default value is 2.

`resample n` - Specifies a constant multiplier for all the sample rates. In this example, all samples are shrunk to 90% of their original length.

`amplify n` - Specifies a constant multiplier for all the sample amplitudes. From 0.0 to 1.0. Default is 0.9. (Any higher than 0.9 is not recommended because of clipping.)

`vmult n` - Specifies a constant multiplier for all `v` (volume command) levels in the MML. Anything above v255 gets $FA $03 $XX applied to it.

`master LLRR` - Specifies the master volume level. LLRR. LL = Left level, RR = Right level

`addmml P:C:R:T:"MML String"` - Adds an text string to the MML. Format: P:C:R:T:"MML String". P = Pattern number, C = Channel number (counting from 1), R = Row number, T = Subtick within row. (All in decimal)

## Commands that can be used in instrument names
Each instrument can have certain parameters associated with them that are translated in a meaningful way in the MML. Use them in the instrument name/file name fields, surrounding the parameters with backticks.

`aDASRGA` - Upon conversion, override the volume envelope with custom ADSR/GAIN. (`aDFA07F` becomes `$DF $A0 $7F`.)

`e` - enable echo for this instrument

`i` - invert volume for this instrument. Not reccomended with CRT TVs (or computers, for that matter...) with only one speaker...

`n` - enable noise for this instrument. (When composing in the tracker, use it with noise.iti or the noise instrument in smw_template.it for a preview of what it'll sound like.)

`p` - enable pitch modulation for this instrument

`rDASRGA` - Release ADSR/GAIN, used when there's a note fade. Same format as `a`

## Stuff that I found out the hard way
- Separators (+++) are not supported
- If it's saying `No such file or directory: 'temp/tunings.txt'`, it's because you need to create the `temp` folder - it won't run if that folder doesn't exist
