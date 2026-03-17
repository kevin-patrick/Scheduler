import csv
import re

def parse_schedule(input_file, output_file):
    records = []
    current_record = None
    meetings = []
    
    with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
        lines = [line.rstrip() for line in f if line.strip()]

    for line in lines:
        # Identify the start of a new class block
        if re.search(r' - [A-Z]{4} \d{4} - \w+$', line) and "Associated Term" not in line:
            if current_record:
                current_record['meetings'] = meetings
                records.append(current_record)
            
            current_record = {'Attributes': ''} # Default empty attributes
            meetings = []
            
            parts = line.split(' - ')
            
            if len(parts) >= 3:
                current_record['Section'] = parts[-1].strip()
                subj_course = parts[-2].strip().split(' ')
                current_record['Subject'] = subj_course[0] if len(subj_course) > 0 else ""
                current_record['Course Number'] = subj_course[1] if len(subj_course) > 1 else ""
                current_record['CRN'] = parts[-3].strip()
            
            if len(parts) >= 5 and "Must be taken with CRN" in parts[-4]:
                current_record['Co-enroll'] = parts[-4].replace("Must be taken with CRN", "").strip()
                current_record['Part of Term'] = parts[-5].strip()
                current_record['Title'] = " - ".join(parts[:-5]).strip()
            elif len(parts) >= 4:
                current_record['Co-enroll'] = ""
                current_record['Part of Term'] = parts[-4].strip()
                current_record['Title'] = " - ".join(parts[:-4]).strip()
                
        elif current_record is not None:
            # NEW: Capture Attributes
            if line.startswith("Attributes:"):
                current_record['Attributes'] = line.replace("Attributes:", "").strip()
            
            elif line.endswith(" Campus"):
                current_record['Campus'] = line.replace(" Campus Campus", " Campus").strip()
            elif line.endswith(" Schedule Type"):
                current_record['Type'] = line.replace(" Schedule Type", "").strip()
            elif line.endswith(" Instructional Method"):
                current_record['Method'] = line.replace(" Instructional Method", "").strip()
            elif line.endswith(" Credits"):
                current_record['Credits'] = line.replace(" Credits", "").strip()
            
            elif re.match(r'^(Class|Laboratory|Clinical|Seminar|Practicum|Combined)\b', line):
                m_parts = line.split('\t')
                if len(m_parts) >= 6:
                    time_str = m_parts[1].strip()
                    days = m_parts[2].strip()
                    where = m_parts[3].strip()
                    instructor = m_parts[6].strip() if len(m_parts) > 6 else ""
                    instructor = re.sub(r'\(P\)?E-mail|,? ?E-mail', '', instructor).strip()
                    
                    if " - " in time_str:
                        t_parts = time_str.split(" - ")
                        start_time = t_parts[0].strip()
                        end_time = t_parts[1].strip()
                    else:
                        start_time = time_str
                        end_time = ""

                    meetings.append({
                        'start_time': start_time, 'end_time': end_time,
                        'days': days, 'where': where, 'instructor': instructor
                    })

    if current_record:
        current_record['meetings'] = meetings
        records.append(current_record)

    headers = [
        'Title', 'Part of Term', 'Co-enroll', 'Attributes', 'CRN', 'Subject', 
        'Course Number', 'Section', 'Campus', 'Type', 'Method', 
        'Credits', 'Start Time', 'End Time', 'Days', 'Where', 'Instructor'
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in records:
            crn = r.get('CRN', '')
            class_meetings = r.get('meetings', [])
            if not class_meetings:
                writer.writerow([
                    r.get('Title', ''), r.get('Part of Term', ''), r.get('Co-enroll', ''), 
                    r.get('Attributes', ''), crn, r.get('Subject', ''), r.get('Course Number', ''), 
                    r.get('Section', ''), r.get('Campus', ''), r.get('Type', ''), 
                    r.get('Method', ''), r.get('Credits', ''), '', '', '', '', ''
                ])
            else:
                for i, m in enumerate(class_meetings):
                    if i == 0:
                        writer.writerow([
                            r.get('Title', ''), r.get('Part of Term', ''), r.get('Co-enroll', ''), 
                            r.get('Attributes', ''), crn, r.get('Subject', ''), r.get('Course Number', ''), 
                            r.get('Section', ''), r.get('Campus', ''), r.get('Type', ''), 
                            r.get('Method', ''), r.get('Credits', ''), m['start_time'], 
                            m['end_time'], m['days'], m['where'], m['instructor']
                        ])
                    else:
                        writer.writerow([
                            '', '', '', '', crn, '', '', '', '', '', '', '', 
                            m['start_time'], m['end_time'], m['days'], m['where'], m['instructor']
                        ])

if __name__ == '__main__':
    parse_schedule('input.txt', 'output.csv')
    print("Parsing complete with Attributes included.")