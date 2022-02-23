import os
import ast
import json
import random
import collections
import numpy as np
import pandas as pd
from PIL import Image
from pathlib import Path
from scipy.ndimage import zoom
import note_seq
from note_seq.protobuf import generator_pb2
from note_seq.protobuf import music_pb2


SCALE_JSON = open(os.path.dirname(__file__) + '{s}scales{s}scales.json'.format(s=os.sep), 'r')
SCALES = json.load(SCALE_JSON)

BASE = {'1': 0, '2': 2, '3': 4, '4': 5, '5': 7, '6': 9, '7': 11}

def _sequence_to_pandas_dataframe(sequence):
    
    """
        Generates a pandas dataframe from a sequence.
        Source: https://github.com/magenta/note-seq/blob/main/note_seq/notebook_utils.py#L122
    """
    pd_dict = collections.defaultdict(list)
    for note in sequence.notes:
        pd_dict['start_time'].append(note.start_time)
        pd_dict['end_time'].append(note.end_time)
        pd_dict['duration'].append(note.end_time - note.start_time)
        pd_dict['pitch'].append(note.pitch)
        pd_dict['bottom'].append(note.pitch - 0.4)
        pd_dict['top'].append(note.pitch + 0.4)
        pd_dict['velocity'].append(note.velocity)
        pd_dict['fill_alpha'].append(note.velocity / 128.0)
        pd_dict['instrument'].append(note.instrument)
        pd_dict['program'].append(note.program)

    # If no velocity differences are found, set alpha to 1.0.
    if np.max(pd_dict['velocity']) == np.min(pd_dict['velocity']):
        pd_dict['fill_alpha'] = [1.0] * len(pd_dict['fill_alpha'])

    return pd.DataFrame(pd_dict)


def show_scales():
    """
        Returns a list of available scales.
    """
    return SCALES.keys()



class ImgToMidi:
    
    image = False
    
    threshold = 200
    midi_range = 127
    default_size = True
    image_bool = None
    midi_start_note = 0
    note_velocity = 80
    downloads_path = False
    offset_start_time = 0.10
    vel = [40,95]
    
    def __init__(self):
        pass
    
    
    def new_midi_file(self):
        """
            Creates new Note Sequence instance.
        """
        self.midi_data = music_pb2.NoteSequence()
        
        
    def _image_resize(self, midi_start_n):
        
        """
            Converts image to B&W given a set threshold
            If default size is left True the image will be compressed to max number of midi notes (127)
            If default size is set False a random part of the image will be processed
            Source : https://stackoverflow.com/a/50090612
        """
        if self.midi_range > 127:
            raise ValueError('Max midi range is 127!')
        
        if self.midi_range + midi_start_n > 127:
            self.midi_range = 127 - midi_start_n
            
        if not self.image:
            raise ValueError('No image provided!')
        else:
            _thresh = self.threshold
            fn = lambda x : 255 if x > _thresh else 0
            r = self.image.convert('L').point(fn, mode='1')
            img_array = np.array(r)

            if self.default_size:
                array = zoom(img_array, self.midi_range/len(img_array))
            else:
                start = random.randint(0, len(img_array)-self.midi_range)
                end = start + self.midi_range
                array = img_array[start:end]
            self.image_bool = array
    
    
    def open_image(self, image_path=False, dl_folder=False):
        
        """
            Open an image from a given path, or set default download folder and open latest image based on timestamp
        """
        if dl_folder:
            d_path = self.downloads_path
            if not d_path:
                raise ValueError('A downloads folder path needs to be set!')

            image_folder = sorted(Path(d_path).iterdir(), key=os.path.getmtime)
            source_image = Image.open(image_folder[-1:][0].__str__())
            self.image = source_image
        else:
            if not image_path:
                raise ValueError('No image path has been provided!')
            source_image = Image.open(image_path)
            self.image = source_image
    
    
    def rand_offset_start_time(self, offset_limit):
        """
            Randomize start time if option selected for notes.
        """
        return random.SystemRandom().uniform(0.01, offset_limit)

    
    def rand_int(self):
        """
            Returns a random value between -1 and 1.
        """
        return random.SystemRandom().randint(-1,1)


    def rand_or_not(self, p, s, e, rand_start_time, rand_note):
        """
            Add a random offset to pitch & start times.
            p : pitch
            s : start time
            e : end_time
            rand_start_time: If True, randomizes start times for notes
            rand_note: If True, changes note values +/- 1
        
        """

        if rand_note == False:
            r_note = 0
        else:
            r_note = self.rand_int()

        if rand_start_time == False:
            self.midi_data.notes.add(pitch=p + r_note, 
                                     start_time=s, 
                                     end_time=e, 
                                     velocity=self.note_velocity)
        else:
            self.midi_data.notes.add(pitch=p + r_note, 
                                     start_time=s + self.rand_offset_start_time(self.offset_start_time), 
                                     end_time=e, 
                                     velocity=self.note_velocity)
            
    def get_seq(self, list_):
        """
            This should probably be refactored.
            Creates the active midi notes from the Image.
        """
        parts = []

        if len(list_) == 1:
            parts.append(list_[0] / 2.0)
            parts.append((list_[0] + 1) / 2.0)

        elif len(list_) == 2:
            if list_[1] - list_[0] != 1:
                parts.append(list_[0] / 2.0)
                parts.append((list_[0] + 1) / 2.0)
                parts.append(list_[1] / 2.0)
                parts.append((list_[1] + 1) / 2.0)
            else:
                parts.append(list_[0] / 2.0)
                parts.append((list_[1] + 1) / 2.0)
        else:
            for n, x in enumerate(list_):
                if n == 0:
                    start = x / 2.0
                    parts.append(start)
                elif x == list_[-1]:
                    if list_[-1] - list_[-2] != 1:
                        parts.append((list_[n-1] + 1) / 2.0)
                        parts.append(x / 2.0)
                        parts.append((x + 1) / 2.0)
                    else:
                        parts.append((x + 1) / 2.0)
                elif x - list_[n-1] == 1:
                    pass
                else:
                    parts.append((list_[n-1] + 1) / 2.0)
                    start = x / 2.0
                    parts.append(start)
        return parts
    
    
    def make_midi(self, 
                  skip=False, 
                  random_start_time=False, 
                  random_note_offset=False, 
                  root_note=0):
        
        midi_sn = self.midi_start_note
        self.new_midi_file()
        self._image_resize(midi_sn)
        
        array = self.image_bool
        if not self.image:
            raise ValueError('No image provided!')
     
        if skip == False:
            array = array[::-1]
            skip = 1
        else:
            array = array[::-1][::skip]
 
        _pitch = midi_sn

        for n, r in enumerate(array, start=1):

            df = pd.DataFrame({'ARR':[x for x in r]})
            df = df.loc[df['ARR'] == False]
            n_sequence = self.get_seq(df.index.tolist())

            if len(n_sequence) % 2 != 0:
                n_sequence.append(len(arr)/2.0)
            if len(n_sequence) / 2 == 1:
                self.rand_or_not(_pitch, 
                                 n_sequence[0], 
                                 n_sequence[1], 
                                 random_start_time, 
                                 random_note_offset)
            else:
                counter = 0
                for x in range(int(len(n_sequence) / 2)):
                    self.rand_or_not(_pitch, 
                                     n_sequence[counter], 
                                     n_sequence[counter+1], 
                                     random_start_time, 
                                     random_note_offset)
                    counter += 2                  

            _pitch += skip

                
                
    def scale(self, scale_name, root_note):
        
        """
            Creates midi note numbers based on a scale.
        """
    
        scale_range = [x * 12 for x in range(1,11)]
        note_list = ast.literal_eval(SCALES[scale_name]['Note Set'])
        midi_notes = []

        for note in note_list:
            if 'bb' in note:
                note = str(int(note[-1]))
                midi_notes.append(BASE[note] - 2)
            elif 'b' in note:
                note = str(int(note[-1]))
                midi_notes.append(BASE[note] - 1)
            elif '#' in note:
                note = str(int(note[-1]))
                midi_notes.append(BASE[note] + 1)
            else:    
                midi_notes.append(BASE[note]) 

        full_scale = []
        for scale in scale_range:
            full_scale.extend([scale + x for x in midi_notes])

        midi_notes.extend(full_scale)
        midi_notes = [x + root_note for x in midi_notes]
        index = [x for x in range(len(midi_notes))]
        return dict(zip(index,midi_notes))
 

    def add_scale(self, scale_set, root):
        """
            Converts existing note values to scaled note values.
        """
        scaled_midi = music_pb2.NoteSequence()
        dataframe = _sequence_to_pandas_dataframe(self.midi_data)
        scaled = self.scale(scale_set, root)
        scaled_notes = list(scaled.values())
        for _pitch in list(set(dataframe['pitch'])):
            if int(_pitch) in scaled_notes:
                pass
            else:
                change_note = min(scaled_notes, key=lambda x:abs(x-int(_pitch)))
                pitchframe = dataframe['pitch'].replace(_pitch, change_note)
                dataframe['pitch'] = list(pitchframe.values)
                
        for i, r in dataframe.iterrows():
            scaled_midi.notes.add(pitch=int(r['pitch']), 
                                  start_time=r['start_time'], 
                                  end_time=r['end_time'], 
                                  velocity=int(r['velocity']))
        self.midi_data = scaled_midi

    
    def stretch(self, bars=16):
        """
            Stretch midi note times set by bars
        """
        stretched_midi = music_pb2.NoteSequence()
        dataframe = _sequence_to_pandas_dataframe(self.midi_data)
        e_time = dataframe.loc[len(dataframe) - 1]['end_time']
        e_time_multiplier = bars / e_time
        dataframe["start_time"] = dataframe["start_time"] * e_time_multiplier
        dataframe["end_time"] = dataframe["end_time"] * e_time_multiplier
        for i, r in dataframe.iterrows():
            stretched_midi.notes.add(pitch=int(r['pitch']), 
                                     start_time=r['start_time'], 
                                     end_time=r['end_time'], 
                                     velocity=int(r['velocity']))
        self.midi_data = stretched_midi
        
        
    def midi_modifier(self, 
                      times=2, 
                      start_zero=False, 
                      rand_vel=False,
                      scale=False,
                      root_note=0,
                      mod_range=16, 
                      scale_change=False,
                      s_stretch=[-7,7],
                      ):
        
        """
            Midi modifier
            times: ?
            start_zero: If set to True shift midi notes to the start.
            rand_vel: If set to True randomizes the note velocities. Can be changed by the `vel` class variable.
            scale: Converts existing note values to given scaled note values.
            root_note: Key note for scale as an integer. (0=C, 4=E)
            mod_range: How many bars to modify for scale shifting.
            scale_change: Will split midi into respective slices and apply shift of notes based on s_stretch values.
            s_stretch: Min/Max distances for midi shifting.
        """
        modified_midi = music_pb2.NoteSequence()
        dataframe = _sequence_to_pandas_dataframe(self.midi_data)
        
        if start_zero:
            min_val = dataframe['start_time'].min()
            dataframe['start_time'] = [x-min_val for x in dataframe['start_time']]
            dataframe['end_time'] = [x-min_val for x in dataframe['end_time']]
                    
        if scale_change != False:
            bar_time = mod_range
            change = scale_change
            split_times = [float(x)*(bar_time/change) for x in range(1,change+1)]
            for times in split_times:
                dataframe.loc[(dataframe['start_time'] < times) & (dataframe['start_time'] >= times - bar_time/change), 'pitch'] = dataframe.loc[(dataframe['start_time'] < times) & (dataframe['start_time'] >= times - bar_time/change), 'pitch'] + random.SystemRandom().randint(s_stretch[0],s_stretch[1])

        if rand_vel:
            dataframe['velocity'] = [random.SystemRandom().randint(self.vel[0], self.vel[1]) for x in dataframe['velocity']]

        for i, r in dataframe.iterrows():
            modified_midi.notes.add(pitch=int(r['pitch']), 
                                    start_time=r['start_time'], 
                                    end_time=r['end_time'], 
                                    velocity=int(r['velocity']))
        
        self.midi_data = modified_midi
        
        if scale:
            self.add_scale(scale, root_note)         

            
            
    def plot(self):
        """
            Renders a bokeh plot for the midi notes.
        """
        return note_seq.plot_sequence(self.midi_data)
    
    
    def save_midi(self, fname=False):
        """
            Exports midi file.
        """
        if fname:
            note_seq.sequence_proto_to_midi_file(self.midi_data, '{}.mid'.format(fname))
        else:
            note_seq.sequence_proto_to_midi_file(self.midi_data, 'img2midi.mid')
