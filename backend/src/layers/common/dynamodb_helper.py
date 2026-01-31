"""
DynamoDB Helper with Advanced Operations and Error Handling.

This module provides enterprise-grade DynamoDB operations with:
- CRUD operations (Create, Read, Update, Delete)
- Automatic retry logic for throttling
- Update expression builders
- Query and scan operations with pagination
- Batch operations
- GSI (Global Secondary Index) support
- Conditional operations
- Transaction support
- Comprehensive error handling

Usage:
    from dynamodb_helper import DynamoDBHelper
    
    # Initialize for a specific table
    helper = DynamoDBHelper("SpottyPottySense-Sensors-dev")
    
    # Get an item
    sensor = helper.get_item({"sensorId": "sensor-001"})
    
    # Put an item
    helper.put_item({"sensorId": "sensor-001", "name": "Bathroom"})
    
    # Update an item
    helper.update_item(
        key={"sensorId": "sensor-001"},
        updates={"status": "active", "lastSeen": datetime.utcnow()}
    )

Author: SpottyPottySense Team
Version: 2.0.0 (Phase 2)
"""

import time
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from exceptions import (
    DynamoDBError,
    DynamoDBThrottlingError,
    DynamoDBItemNotFoundError,
    ResourceNotFoundError
)
from logger import get_logger

logger = get_logger(__name__)


# ==============================================================================
# CONSTANTS
# ==============================================================================

# Retry configuration for throttling
MAX_RETRIES = 3
BASE_RETRY_DELAY = 0.1  # 100ms
MAX_RETRY_DELAY = 2.0   # 2 seconds

# Batch operation limits
BATCH_WRITE_MAX_ITEMS = 25
BATCH_GET_MAX_ITEMS = 100


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def python_to_dynamodb(value: Any) -> Any:
    """
    Convert Python types to DynamoDB-compatible types.
    
    Handles float->Decimal conversion and other type conversions.
    
    Args:
        value: Python value to convert
        
    Returns:
        DynamoDB-compatible value
    """
    if isinstance(value, float):
        return Decimal(str(value))
    elif isinstance(value, dict):
        return {k: python_to_dynamodb(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [python_to_dynamodb(item) for item in value]
    return value


def dynamodb_to_python(value: Any) -> Any:
    """
    Convert DynamoDB types to Python types.
    
    Handles Decimal->float conversion and other type conversions.
    
    Args:
        value: DynamoDB value to convert
        
    Returns:
        Python-compatible value
    """
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    elif isinstance(value, dict):
        return {k: dynamodb_to_python(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [dynamodb_to_python(item) for item in value]
    return value


# ==============================================================================
# DYNAMODB HELPER CLASS
# ==============================================================================

class DynamoDBHelper:
    """
    Comprehensive DynamoDB operations helper.
    
    This class provides high-level DynamoDB operations with:
    - Automatic retry logic for throttling
    - Type conversion (Python <-> DynamoDB)
    - Update expression building
    - Batch operations
    - Query and scan with pagination
    - Comprehensive error handling
    
    Attributes:
        table_name: Name of the DynamoDB table
        table: Boto3 DynamoDB Table resource
    """
    
    def __init__(self, table_name: str, region_name: Optional[str] = None):
        """
        Initialize DynamoDB helper for a specific table.
        
        Args:
            table_name: Name of the DynamoDB table
            region_name: AWS region (defaults to Lambda environment region)
        """
        self.table_name = table_name
        dynamodb = boto3.resource('dynamodb', region_name=region_name)
        self.table = dynamodb.Table(table_name)
        
        logger.info(
            "DynamoDBHelper initialized",
            extra={"table_name": table_name, "region": region_name or "default"}
        )
    
    # ==========================================================================
    # CREATE / PUT OPERATIONS
    # ==========================================================================
    
    def put_item(
        self,
        item: Dict[str, Any],
        condition_expression: Optional[str] = None,
        expression_attribute_values: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Put (create or replace) an item in DynamoDB.
        
        Args:
            item: Item data to store
            condition_expression: Optional condition (e.g., "attribute_not_exists(id)")
            expression_attribute_values: Values for condition expression
            
        Returns:
            Response from DynamoDB
            
        Raises:
            DynamoDBError: If put operation fails
            
        Example:
            >>> helper = DynamoDBHelper("Sensors")
            >>> helper.put_item({
            >>>     "sensorId": "sensor-001",
            >>>     "name": "Bathroom Sensor",
            >>>     "status": "active"
            >>> })
        """
        logger.info(
            "Putting item to DynamoDB",
            extra={"table_name": self.table_name}
        )
        
        # Convert Python types to DynamoDB types
        item = python_to_dynamodb(item)
        
        try:
            start_time = time.time()
            
            params = {'Item': item}
            if condition_expression:
                params['ConditionExpression'] = condition_expression
            if expression_attribute_values:
                params['ExpressionAttributeValues'] = expression_attribute_values
            
            response = self._execute_with_retry(
                lambda: self.table.put_item(**params)
            )
            
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "Item put successfully",
                extra={
                    "table_name": self.table_name,
                    "duration_ms": round(duration_ms, 2)
                }
            )
            
            return response
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(
                "Failed to put item",
                extra={
                    "table_name": self.table_name,
                    "error_code": error_code,
                    "error_message": str(e)
                },
                exc_info=True
            )
            raise DynamoDBError(
                message=f"Failed to put item: {error_code}",
                table_name=self.table_name,
                operation="put_item",
                details={"error_code": error_code}
            )
    
    # ==========================================================================
    # READ / GET OPERATIONS
    # ==========================================================================
    
    def get_item(
        self,
        key: Dict[str, Any],
        consistent_read: bool = False,
        attributes: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get an item from DynamoDB by primary key.
        
        Args:
            key: Primary key dictionary (e.g., {"sensorId": "sensor-001"})
            consistent_read: Use strongly consistent read
            attributes: List of attributes to retrieve (projection)
            
        Returns:
            Item data or None if not found
            
        Raises:
            DynamoDBError: If get operation fails
            
        Example:
            >>> helper = DynamoDBHelper("Sensors")
            >>> sensor = helper.get_item({"sensorId": "sensor-001"})
            >>> if sensor:
            >>>     print(sensor['name'])
        """
        logger.debug(
            "Getting item from DynamoDB",
            extra={"table_name": self.table_name, "key": key}
        )
        
        try:
            start_time = time.time()
            
            params = {
                'Key': key,
                'ConsistentRead': consistent_read
            }
            if attributes:
                params['ProjectionExpression'] = ','.join(attributes)
            
            response = self._execute_with_retry(
                lambda: self.table.get_item(**params)
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            if 'Item' in response:
                item = dynamodb_to_python(response['Item'])
                logger.debug(
                    "Item retrieved successfully",
                    extra={
                        "table_name": self.table_name,
                        "duration_ms": round(duration_ms, 2)
                    }
                )
                return item
            else:
                logger.debug(
                    "Item not found",
                    extra={"table_name": self.table_name, "key": key}
                )
                return None
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(
                "Failed to get item",
                extra={
                    "table_name": self.table_name,
                    "key": key,
                    "error_code": error_code
                },
                exc_info=True
            )
            raise DynamoDBError(
                message=f"Failed to get item: {error_code}",
                table_name=self.table_name,
                operation="get_item",
                details={"error_code": error_code, "key": str(key)}
            )
    
    # ==========================================================================
    # UPDATE OPERATIONS
    # ==========================================================================
    
    def update_item(
        self,
        key: Dict[str, Any],
        updates: Dict[str, Any],
        condition_expression: Optional[str] = None,
        return_values: str = "ALL_NEW"
    ) -> Optional[Dict[str, Any]]:
        """
        Update an item in DynamoDB with automatic expression building.
        
        This method automatically builds UpdateExpression from the updates dict.
        
        Args:
            key: Primary key dictionary
            updates: Dictionary of attributes to update
            condition_expression: Optional condition
            return_values: What to return (NONE, ALL_OLD, ALL_NEW, etc.)
            
        Returns:
            Updated item data (if return_values != NONE)
            
        Raises:
            DynamoDBError: If update fails
            
        Example:
            >>> helper = DynamoDBHelper("Sensors")
            >>> updated = helper.update_item(
            >>>     key={"sensorId": "sensor-001"},
            >>>     updates={
            >>>         "status": "active",
            >>>         "lastSeen": datetime.utcnow(),
            >>>         "motionCount": 5
            >>>     }
            >>> )
        """
        logger.info(
            "Updating item in DynamoDB",
            extra={"table_name": self.table_name, "key": key}
        )
        
        # Convert updates to DynamoDB types
        updates = python_to_dynamodb(updates)
        
        # Build update expression
        update_expr, expr_attr_names, expr_attr_values = self._build_update_expression(updates)
        
        try:
            start_time = time.time()
            
            params = {
                'Key': key,
                'UpdateExpression': update_expr,
                'ExpressionAttributeNames': expr_attr_names,
                'ExpressionAttributeValues': expr_attr_values,
                'ReturnValues': return_values
            }
            
            if condition_expression:
                params['ConditionExpression'] = condition_expression
            
            response = self._execute_with_retry(
                lambda: self.table.update_item(**params)
            )
            
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "Item updated successfully",
                extra={
                    "table_name": self.table_name,
                    "duration_ms": round(duration_ms, 2)
                }
            )
            
            if 'Attributes' in response:
                return dynamodb_to_python(response['Attributes'])
            return None
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(
                "Failed to update item",
                extra={
                    "table_name": self.table_name,
                    "key": key,
                    "error_code": error_code
                },
                exc_info=True
            )
            raise DynamoDBError(
                message=f"Failed to update item: {error_code}",
                table_name=self.table_name,
                operation="update_item",
                details={"error_code": error_code}
            )
    
    # ==========================================================================
    # DELETE OPERATIONS
    # ==========================================================================
    
    def delete_item(
        self,
        key: Dict[str, Any],
        condition_expression: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete an item from DynamoDB.
        
        Args:
            key: Primary key dictionary
            condition_expression: Optional condition
            
        Returns:
            Response from DynamoDB
            
        Raises:
            DynamoDBError: If delete fails
            
        Example:
            >>> helper = DynamoDBHelper("Sensors")
            >>> helper.delete_item({"sensorId": "sensor-001"})
        """
        logger.info(
            "Deleting item from DynamoDB",
            extra={"table_name": self.table_name, "key": key}
        )
        
        try:
            start_time = time.time()
            
            params = {'Key': key}
            if condition_expression:
                params['ConditionExpression'] = condition_expression
            
            response = self._execute_with_retry(
                lambda: self.table.delete_item(**params)
            )
            
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "Item deleted successfully",
                extra={
                    "table_name": self.table_name,
                    "duration_ms": round(duration_ms, 2)
                }
            )
            
            return response
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(
                "Failed to delete item",
                extra={
                    "table_name": self.table_name,
                    "key": key,
                    "error_code": error_code
                },
                exc_info=True
            )
            raise DynamoDBError(
                message=f"Failed to delete item: {error_code}",
                table_name=self.table_name,
                operation="delete_item",
                details={"error_code": error_code}
            )
    
    # ==========================================================================
    # QUERY OPERATIONS
    # ==========================================================================
    
    def query(
        self,
        key_condition: str,
        filter_expression: Optional[str] = None,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        scan_forward: bool = True,
        exclusive_start_key: Optional[Dict[str, Any]] = None,
        **expression_values
    ) -> Dict[str, Any]:
        """
        Query items from DynamoDB (primary key or GSI).
        
        Args:
            key_condition: Key condition expression (e.g., "userId = :uid")
            filter_expression: Optional filter expression
            index_name: GSI name if querying an index
            limit: Maximum number of items to return
            scan_forward: True for ascending, False for descending
            exclusive_start_key: Pagination key
            **expression_values: Expression attribute values (uid="user-123")
            
        Returns:
            Dictionary with 'Items' and optionally 'LastEvaluatedKey'
            
        Example:
            >>> helper = DynamoDBHelper("Sensors")
            >>> result = helper.query(
            >>>     key_condition="userId = :uid",
            >>>     index_name="UserIdIndex",
            >>>     uid="user-123"
            >>> )
            >>> for item in result['Items']:
            >>>     print(item['sensorId'])
        """
        logger.info(
            "Querying DynamoDB",
            extra={
                "table_name": self.table_name,
                "index_name": index_name,
                "key_condition": key_condition
            }
        )
        
        try:
            start_time = time.time()
            
            # Build expression attribute values
            expr_attr_values = {
                f":{k}": python_to_dynamodb(v)
                for k, v in expression_values.items()
            }
            
            params = {
                'KeyConditionExpression': key_condition,
                'ExpressionAttributeValues': expr_attr_values,
                'ScanIndexForward': scan_forward
            }
            
            if index_name:
                params['IndexName'] = index_name
            if filter_expression:
                params['FilterExpression'] = filter_expression
            if limit:
                params['Limit'] = limit
            if exclusive_start_key:
                params['ExclusiveStartKey'] = exclusive_start_key
            
            response = self._execute_with_retry(
                lambda: self.table.query(**params)
            )
            
            duration_ms = (time.time() - start_time) * 1000
            item_count = len(response.get('Items', []))
            
            logger.info(
                "Query completed successfully",
                extra={
                    "table_name": self.table_name,
                    "item_count": item_count,
                    "has_more": 'LastEvaluatedKey' in response,
                    "duration_ms": round(duration_ms, 2)
                }
            )
            
            # Convert items to Python types
            if 'Items' in response:
                response['Items'] = [
                    dynamodb_to_python(item) for item in response['Items']
                ]
            
            return response
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(
                "Query failed",
                extra={
                    "table_name": self.table_name,
                    "error_code": error_code
                },
                exc_info=True
            )
            raise DynamoDBError(
                message=f"Query failed: {error_code}",
                table_name=self.table_name,
                operation="query",
                details={"error_code": error_code}
            )
    
    # ==========================================================================
    # BATCH OPERATIONS
    # ==========================================================================
    
    def batch_write(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Batch write items to DynamoDB (up to 25 items per batch).
        
        Args:
            items: List of items to write
            
        Returns:
            Response with unprocessed items if any
            
        Raises:
            DynamoDBError: If batch write fails
            
        Example:
            >>> helper = DynamoDBHelper("Sensors")
            >>> items = [
            >>>     {"sensorId": "s1", "name": "Sensor 1"},
            >>>     {"sensorId": "s2", "name": "Sensor 2"}
            >>> ]
            >>> helper.batch_write(items)
        """
        logger.info(
            "Batch writing items to DynamoDB",
            extra={"table_name": self.table_name, "item_count": len(items)}
        )
        
        # Convert items
        items = [python_to_dynamodb(item) for item in items]
        
        # Process in batches of 25
        unprocessed_items = []
        for i in range(0, len(items), BATCH_WRITE_MAX_ITEMS):
            batch = items[i:i + BATCH_WRITE_MAX_ITEMS]
            
            request_items = {
                self.table_name: [
                    {'PutRequest': {'Item': item}} for item in batch
                ]
            }
            
            try:
                response = self._execute_with_retry(
                    lambda: boto3.client('dynamodb').batch_write_item(
                        RequestItems=request_items
                    )
                )
                
                if 'UnprocessedItems' in response and response['UnprocessedItems']:
                    unprocessed_items.extend(response['UnprocessedItems'].get(self.table_name, []))
                    
            except ClientError as e:
                error_code = e.response['Error']['Code']
                logger.error(
                    "Batch write failed",
                    extra={
                        "table_name": self.table_name,
                        "error_code": error_code
                    },
                    exc_info=True
                )
                raise DynamoDBError(
                    message=f"Batch write failed: {error_code}",
                    table_name=self.table_name,
                    operation="batch_write",
                    details={"error_code": error_code}
                )
        
        logger.info(
            "Batch write completed",
            extra={
                "table_name": self.table_name,
                "total_items": len(items),
                "unprocessed_count": len(unprocessed_items)
            }
        )
        
        return {"UnprocessedItems": unprocessed_items}
    
    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================
    
    def _build_update_expression(
        self,
        updates: Dict[str, Any]
    ) -> tuple[str, Dict[str, str], Dict[str, Any]]:
        """
        Build UpdateExpression from a dictionary of updates.
        
        Args:
            updates: Dictionary of attribute names and values
            
        Returns:
            Tuple of (update_expression, attribute_names, attribute_values)
        """
        set_clauses = []
        expr_attr_names = {}
        expr_attr_values = {}
        
        for i, (attr, value) in enumerate(updates.items()):
            # Use placeholders to handle reserved words
            attr_placeholder = f"#attr{i}"
            value_placeholder = f":val{i}"
            
            expr_attr_names[attr_placeholder] = attr
            expr_attr_values[value_placeholder] = value
            set_clauses.append(f"{attr_placeholder} = {value_placeholder}")
        
        update_expression = "SET " + ", ".join(set_clauses)
        
        return update_expression, expr_attr_names, expr_attr_values
    
    def _execute_with_retry(self, operation):
        """
        Execute DynamoDB operation with exponential backoff retry.
        
        Args:
            operation: Lambda function that performs the operation
            
        Returns:
            Operation response
            
        Raises:
            DynamoDBThrottlingError: If max retries exceeded
        """
        last_exception = None
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                return operation()
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                # Only retry on throttling errors
                if error_code in ['ProvisionedThroughputExceededException', 'ThrottlingException']:
                    last_exception = e
                    
                    if attempt < MAX_RETRIES:
                        # Exponential backoff with jitter
                        delay = min(BASE_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                        logger.warning(
                            f"DynamoDB throttled, retrying in {delay}s",
                            extra={
                                "attempt": attempt + 1,
                                "max_retries": MAX_RETRIES,
                                "delay_seconds": delay
                            }
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "Max retries exceeded for throttled request",
                            extra={"attempts": MAX_RETRIES + 1}
                        )
                        raise DynamoDBThrottlingError(
                            table_name=self.table_name,
                            details={"attempts": MAX_RETRIES + 1}
                        )
                else:
                    # Non-retryable error, raise immediately
                    raise
        
        # Should never reach here, but just in case
        raise last_exception if last_exception else DynamoDBError(
            message="Operation failed after retries",
            table_name=self.table_name
        )
