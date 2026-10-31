-- S1-DBA-02 (1/4): HOPE base tables. Structure only, no data.
-- Source: HopeDB_audit.sql (DROP TABLE and SELECT lines removed on purpose).

CREATE TABLE employee (empno VARCHAR(5) NOT NULL PRIMARY KEY, 
 lastname VARCHAR(15), 
 firstname VARCHAR(15), 
 gender CHAR(1) CONSTRAINT gender_ck CHECK (gender in ('M','F')), 
 birthdate DATE, 
 hiredate DATE, 
 sepDate DATE);

CREATE TABLE department (deptCode VARCHAR(3) NOT NULL,
 deptName VARCHAR (20), 
 PRIMARY KEY (deptCode));

CREATE TABLE job (jobCode VARCHAR(4) NOT NULL PRIMARY KEY, 
 jobDesc VARCHAR(20));

CREATE TABLE jobHistory (empNo VARCHAR(5) NOT NULL REFERENCES employee,
 jobCode VARCHAR(4) NOT NULL REFERENCES job, 
 effDate DATE NOT NULL , 
 salary DECIMAL(10,2) CONSTRAINT salary_ck 
 CHECK (salary >= 0.0), deptCode VARCHAR(4),
 PRIMARY KEY (empNo, jobCode,effDate), 
 FOREIGN KEY (deptCode) REFERENCES department);

CREATE TABLE customer (custno VARCHAR(5) NOT NULL PRIMARY KEY, 
 custname VARCHAR(20), 
 address VARCHAR(50), 
 payterm VARCHAR(3) CONSTRAINT pay_ck 
 CHECK (payterm IN ('COD', '30D', '45D')));

CREATE TABLE sales (transNo VARCHAR(8) NOT NULL PRIMARY KEY, 
 salesDate DATE, 
 custNo VARCHAR(5), 
 empNo VARCHAR(5), 
 FOREIGN KEY (custNo) REFERENCES customer, 
 FOREIGN KEY (empno) REFERENCES employee);

CREATE TABLE product (prodCode VARCHAR(6) NOT NULL PRIMARY KEY, 
 description VARCHAR(30), 
 unit VARCHAR(3) CONSTRAINT unit_ck 
 CHECK (unit IN ('pc','ea','mtr','pkg','ltr')));

CREATE TABLE salesDetail (transNo VARCHAR(8) NOT NULL REFERENCES sales, 
 prodCode VARCHAR(6) NOT NULL REFERENCES product, 
 quantity DECIMAL(10,2) CONSTRAINT quantity_ck 
 CHECK (quantity >= 0.0), 
 PRIMARY KEY (transNo, prodCode));

CREATE TABLE payment (orNo VARCHAR(8) NOT NULL PRIMARY KEY, 
 payDate DATE, 
 amount DECIMAL(10,2), 
 transno VARCHAR(8) REFERENCES sales);

CREATE TABLE priceHist (effDate DATE NOT NULL, 
 prodCode VARCHAR(6) NOT NULL REFERENCES product, 
 unitPrice DECIMAL(10,2) CONSTRAINT unitP_ck 
 CHECK (unitPrice > 0), 
 PRIMARY KEY (effDate, prodCode));
