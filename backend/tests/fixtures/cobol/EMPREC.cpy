      * EMPREC.cpy Copybook
       01  EMP-RECORD.
           05  EMP-ID             PIC X(6).
           05  EMP-NAME           PIC X(25).
           05  EMP-TYPE           PIC X(1).
               88  FULL-TIME      VALUE 'F'.
               88  PART-TIME      VALUE 'P'.
           05  EMP-HOURS          PIC 9(3)V99.
           05  EMP-RATE           PIC 9(3)V99.
           05  EMP-STATUS         PIC X(1).
               88  ACTIVE-STATUS  VALUE 'A'.
               88  INACTIVE-STATUS VALUE 'I'.
