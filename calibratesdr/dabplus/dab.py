import numpy as np
import calibratesdr as cali

def get_ppm(data, samplerate = 2048000):
    adc_offset = -127

    data_slice = (adc_offset + data[0:: 2]) + 1j * (adc_offset + data[1:: 2])

    signal = np.abs(data_slice)


    signal_meaned = cali.utils.movingaverage(signal, 80)


    #signal_mean = np.mean(signal_meaned)

    #low = signal_mean / 2.0
    #signal_gaps = np.copy(signal_meaned)
    #signal_gaps[signal_gaps > signal_mean / 2.0] = signal_mean
    #signal_gaps[signal_gaps <= signal_mean / 2.0] = low

    signal_mean = np.mean(signal_meaned)
    low = (signal_mean + np.min(signal_meaned)) / 2.0

    signal_gaps = np.copy(signal_meaned)
    signal_gaps[signal_gaps > low] = signal_mean
    signal_gaps[signal_gaps <= low] = low

    counter_gap = 0

    gap_length = []
    gap_position = []

    transmission_frame_duration = 0.096  # sec
    transmission_frame_samples = samplerate * transmission_frame_duration

    for i in range(len(signal_gaps)):
        if signal_gaps[i] == low:
            counter_gap += 1

        if counter_gap > 0 and signal_gaps[i] != low:
            #print(i, counter_gap)
            gap_length.append(counter_gap)
            gap_position.append(i - counter_gap)
            counter_gap = 0


    null_symbol_duration = int(2656 * samplerate / 2048000.0)

    # finding the null gap that is closest to the null symbol duration
    needle_index = 0
    needle_gap = 0
    for i in range(len(gap_length)):
        if i == 0 or np.abs(gap_length[i] - null_symbol_duration) < needle_gap:
            needle_index = i
            needle_gap = np.abs(gap_length[i] - null_symbol_duration)


    # needle can reach out of data. no check yet
    needle = signal_meaned[gap_position[needle_index] + gap_length[needle_index] + 200:
                           gap_position[needle_index] + gap_length[needle_index] + 2400]

    needle2 = np.sum(np.multiply(needle, needle))
    window = len(needle)

    cor_result = np.zeros(len(signal_meaned))

    for i in range(len(gap_position)):

        end = gap_position[i] + gap_length[i] + 4000
        if gap_length[i] > 500:# and end < len(signal_meaned)-1: # needle could range into end of signal

            start = gap_position[i] + gap_length[i] - 100
            haystack = signal_meaned[start: end]

            for j in range(0, len(haystack) - len(needle)):
                haystack_part = np.array(haystack[j: j + window])
                normed_cross_correlation = np.sum(np.multiply(haystack_part, needle))
                normed_cross_correlation = normed_cross_correlation / \
                                           (np.sum(np.multiply(haystack_part, haystack_part)) * needle2) ** 0.5

                cor_result[start + j] = normed_cross_correlation * 100.0

    gap_location = []
    gap_location_pin = []

    for i in range(0, len(cor_result), int(transmission_frame_samples)):
        haystack = cor_result[i: i + int(transmission_frame_samples)]

        if np.max(haystack) > 0.0 and i > 0:

            index_max = i + np.argmax(haystack)

            gap_location.append(index_max)
            gap_location_pin.append(70)


    # delete the outliers
    dif = np.diff(gap_location)

    ppm = None

    if len(dif) > 8:

        dif = cali.utils.reduce_outliers(dif)

        # calculate the ppm
        total_samples_measured = np.sum(dif)
        total_samples = len(dif) * samplerate * transmission_frame_duration
        ppm_measured = total_samples - total_samples_measured
        if total_samples_measured > 0:
            factor = total_samples_measured / 1000000
            ppm = ppm_measured / factor
        else:
            ppm = None

    else:
        ppm = None

    return ppm


if __name__ == '__main__':
    print("this is dab support so far")