       IDENTIFICATION DIVISION.
       PROGRAM-ID. ACCTMNT.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-DATE-X           PIC X(8).
       01  WS-DATE             REDEFINES WS-DATE-X.
           05  WS-YEAR         PIC 9(4).
           05  WS-MONTH        PIC 9(2).
           05  WS-DAY          PIC 9(2).
       01  WS-ACCOUNT-RECORD.
           05  ACCT-NUM        PIC X(10).
           05  ACCT-BAL        PIC S9(9)V99 COMP-3.
           05  ACCT-OPT        PIC 9(1).
       01  WS-TABLE.
           05  WS-ITEM OCCURS 10 TIMES INDEXED BY WS-IDX.
               10  WS-CODE     PIC X(3).
               10  WS-DESC     PIC X(20).

       PROCEDURE DIVISION.
       START-HERE.
           MOVE "20261014" TO WS-DATE-X.

       MENU.
           GO TO DO-DEPOSIT DO-WITHDRAW SHOW-BAL
               DEPENDING ON ACCT-OPT.

       DO-DEPOSIT.
           ADD 100 TO ACCT-BAL
           GO TO MENU.

       DO-WITHDRAW.
           SUBTRACT 50 FROM ACCT-BAL
           GO TO MENU.

       SHOW-BAL.
           SEARCH WS-ITEM
               AT END
                   DISPLAY "NOT FOUND"
               WHEN WS-CODE (WS-IDX) = "ACT"
                   DISPLAY ACCT-BAL
           END-SEARCH
           GO TO MENU.
