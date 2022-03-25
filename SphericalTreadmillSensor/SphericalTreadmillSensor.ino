//Spherical Treadmill Sensor: This code is designed for the Teensy 3.5, and forwards
//ADNS-5050 optical sensor data and timestamps to a computer via serial.
//Author: Grayson Derossi
//Email: gderossi@wustl.edu

#include <SPI.h>

//Bytes that serve as headers to Serial data to let computer know what it is receiving
const byte DAQ_SYNC_IDENTIFIER = '1';
const byte ODOR_ON_IDENTIFIER = '2';
const byte ODOR_OFF_IDENTIFIER = '3';
const byte OPTICAL_SENSOR_DATA_IDENTIFIER = '4';

//Optical sensor register numbers
const byte MOTION_REGISTER = 0x02;
const byte DELTA_X_REGISTER = 0x03;
const byte DELTA_Y_REGISTER = 0x04;

//Bit header to tell sensor if serial request is a read or write
const byte SPI_READ = 0x00;
const byte SPI_WRITE = 0x80;

//Microsecond timing delays necessary between I/O operations
const int READ_DELAY = 1;
const int WRITE_READ_DELAY = 20;
const int WRITE_WRITE_DELAY = 30;

//Pins for timing signal inputs
const int DAQ_SYNC_PIN = 2;
const int ODOR_SIGNAL_PIN = 3;

//Pins for SPI interface with optical sensor peripheral
const int OPTICAL_SENSOR_CHIP_SELECT_PIN = 28;
const int OPTICAL_SENSOR_RESET_PIN = 27;
const int PRIMARY_SDO_PIN = 11;
const int ALTERNATE_SDO_PIN = 7;

unsigned long daqSyncTime;      //Stores timestamp of last DAQ sync TTL signal
volatile bool daqSyncTimeReady; //Is daqSyncTime updated but not written to Serial?

unsigned long odorOnTime;       //Stores timestamp of last odor on TTL signal
unsigned long odorOffTime;      //Stores timestamp of last odor off TTL signal
bool odorOn;                    //Is odorant currently being released?
volatile bool odorOnTimeReady;  //Is odorOnTime updated but not written to Serial?
volatile bool odorOffTimeReady; //Is odorOffTime updated but not written to Serial?

byte motionUpdate;              //Has position changed since last check?
byte deltaX;                    //Change in x value, from optical sensor (2's comp)
byte deltaY;                    //Change in y value, from optical sensor (2's comp)
unsigned long motionTimestamp;  //Stores timestamp of last motion update

void setup() {
  Serial.begin(115200);
  
  pinMode(DAQ_SYNC_PIN, INPUT);
  pinMode(ODOR_SIGNAL_PIN, INPUT);
  pinMode(OPTICAL_SENSOR_CHIP_SELECT_PIN, OUTPUT);
  pinMode(OPTICAL_SENSOR_RESET_PIN, OUTPUT);

  digitalWrite(OPTICAL_SENSOR_RESET_PIN, HIGH); //Keep reset pin high to enable sensor

  attachInterrupt(digitalPinToInterrupt(DAQ_SYNC_PIN), updateDaqSyncTime, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ODOR_SIGNAL_PIN), updateOdorTime, CHANGE);

  odorOn = false;
  daqSyncTimeReady = false;
  odorOnTimeReady = false;
  odorOffTimeReady = false;
  motionUpdate = false;

  SPI.begin();
  delay(1000);
}

void loop() {
  //Check if TTL timestamps are updated, and write to Serial if so
  if(daqSyncTimeReady)
  {
    Serial.write(DAQ_SYNC_IDENTIFIER); // 1 byte
    Serial.write(daqSyncTime);         // 4 bytes
    daqSyncTimeReady = false;
  }
  if(odorOnTimeReady)
  {
    Serial.write(ODOR_ON_IDENTIFIER);  // 1 byte
    Serial.write(odorOnTime);          // 4 bytes
    odorOnTimeReady = false;
  }
  if(odorOffTimeReady)
  {
    Serial.write(ODOR_OFF_IDENTIFIER);  // 1 byte
    Serial.write(odorOffTime);          // 4 bytes
    odorOffTimeReady = false;
  }

  //Check for optical sensor updates over SPI
  //Read Motion register
  motionUpdate = readSPI(MOTION_REGISTER) >> 7; //Get motion bit (bit 7)

  //If motion occurred, read Delta_X and Delta_Y registers
  if(motionUpdate)
  {
   deltaX = readSPI(DELTA_X_REGISTER);
   deltaY = readSPI(DELTA_Y_REGISTER);
   motionTimestamp = micros();
  }

  //Write optical sensor data to Serial
  if(motionUpdate)
  {
    Serial.write(OPTICAL_SENSOR_DATA_IDENTIFIER); // 1 byte
    Serial.write(deltaX);                         // 1 byte
    Serial.write(deltaY);                         // 1 byte
    Serial.write(motionTimestamp);                // 4 bytes
  }
}

byte readSPI(byte targetRegister)
{
  byte dataReceived;
  SPI.beginTransaction(SPISettings(3000000, MSBFIRST, SPI_MODE3));
  digitalWrite(OPTICAL_SENSOR_CHIP_SELECT_PIN, LOW);
  dataReceived = SPI.transfer(targetRegister | SPI_READ);
  delayMicroseconds(READ_DELAY);
  SPI.setMOSI(ALTERNATE_SDO_PIN); //Set output pin to alternate to allow proper reading
  dataReceived = SPI.transfer(0x00);
  SPI.setMOSI(PRIMARY_SDO_PIN); //Reset output pin
  delayMicroseconds(READ_DELAY);
  digitalWrite(OPTICAL_SENSOR_CHIP_SELECT_PIN, HIGH);
  SPI.endTransaction();
  return dataReceived;
}

//Interrupt Service Routines

//Update the DAQ sync variable and allow Serial write
void updateDaqSyncTime()
{
  daqSyncTime = micros();
  daqSyncTimeReady = true;
}

//Update odor state and appropriate odor timestamp, then allow Serial write
void updateOdorTime()
{
  if(odorOn)
  {
    odorOffTime = micros();
    odorOffTimeReady = true;
  }
  else
  {
    odorOnTime = micros();
    odorOnTimeReady = true;
  }

  odorOn = !odorOn;
}
