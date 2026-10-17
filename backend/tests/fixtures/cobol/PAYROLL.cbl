       IDENTIFICATION DIVISION.
       PROGRAM-ID. PAYROLL.
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT EMP-FILE ASSIGN TO "EMP.DAT"
               ORGANIZATION IS LINE SEQUENTIAL.
           SELECT RPT-FILE ASSIGN TO "PAYROLL.RPT"
               ORGANIZATION IS LINE SEQUENTIAL.
       DATA DIVISION.
       FILE SECTION.
       FD  EMP-FILE.
       01  EMP-FILE-REC        PIC X(80).
       FD  RPT-FILE.
       01  RPT-FILE-REC        PIC X(120).
       WORKING-STORAGE SECTION.
       01  WS-FLAGS.
           05  WS-EOF-FLAG     PIC X(1) VALUE 'N'.
               88  END-OF-FILE VALUE 'Y'.
               88  MORE-DATA   VALUE 'N'.
       01  WS-TOTALS.
           05  WS-GROSS-PAY    PIC 9(7)V99 VALUE ZERO.
           05  WS-TAX          PIC 9(7)V99 VALUE ZERO.
           05  WS-NET-PAY      PIC 9(7)V99 VALUE ZERO.
       01  WS-CALC-TIER        PIC X(1).

       COPY EMPREC.

       PROCEDURE DIVISION.
       0000-MAIN.
           OPEN INPUT EMP-FILE
           OPEN OUTPUT RPT-FILE
           PERFORM 1000-READ
           PERFORM 2000-PROCESS UNTIL END-OF-FILE
           CLOSE EMP-FILE
           CLOSE RPT-FILE
           STOP RUN.

       1000-READ.
           READ EMP-FILE INTO EMP-RECORD
               AT END
                   MOVE 'Y' TO WS-EOF-FLAG
           END-READ.

       2000-PROCESS.
           IF FULL-TIME
               COMPUTE WS-GROSS-PAY = EMP-HOURS * EMP-RATE
           ELSE
               COMPUTE WS-GROSS-PAY = EMP-HOURS * (EMP-RATE * 0.9)
           END-IF

           EVALUATE WS-GROSS-PAY
               WHEN 0 THRU 1000
                   MOVE '1' TO WS-CALC-TIER
               WHEN 1001 THRU 3000
                   MOVE '2' TO WS-CALC-TIER
               WHEN OTHER
                   MOVE '3' TO WS-CALC-TIER
           END-EVALUATE

           EVALUATE WS-CALC-TIER
               WHEN '1'
                   COMPUTE WS-TAX = WS-GROSS-PAY * 0.10
               WHEN '2'
                   COMPUTE WS-TAX = WS-GROSS-PAY * 0.20
               WHEN '3'
                   COMPUTE WS-TAX = WS-GROSS-PAY * 0.30
           END-EVALUATE

           COMPUTE WS-NET-PAY = WS-GROSS-PAY - WS-TAX
           WRITE RPT-FILE-REC FROM EMP-NAME
           PERFORM 1000-READ.
